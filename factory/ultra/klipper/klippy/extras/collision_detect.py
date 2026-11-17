# Real-time Collision & Stall Detection for Klipper
#
# Copyright (C) 2024
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging
import math

class CollisionDetect:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.reactor = self.printer.get_reactor()
        
        # settings (unit: m/s²)
        self.threshold = config.getfloat('threshold', default=15.0, above=0.0)
        self.window_size = config.getint('window_size', default=2, minval=1)
        self.warmup_time = config.getfloat('warmup_time', default=0.2, minval=0.0)
        self.cooldown_time = config.getfloat('cooldown_time', default=1.0, minval=0.1)
        self.action = config.get('action', default='shutdown').lower()
        self.sensor_name = config.get('sensor', default='lis2dw')
        
        # hardware and low level
        self.sensor_obj = None
        self.batch_bulk = None
        
        # run state
        self.is_monitoring = False
        self.is_debugging = False
        self.debug_end_time = 0.0
        self.debug_timer = None
        
        # algorithm and statistics variables
        self.debug_peak = 0.0
        self.sample_counter = 0
        self.debug_samples = []
        self.prev_mag = None
        self.consecutive_hits = 0
        self.last_trigger_time = 0.0
        self.start_time = 0.0
        self.is_handling_trigger = False
        
        # register the G-code commands
        self.gcode.register_command("COLLISION_DETECT_ENABLE", self.cmd_ENABLE)
        self.gcode.register_command("COLLISION_DETECT_DISABLE", self.cmd_DISABLE)
        self.gcode.register_command("SET_COLLISION_THRESHOLD", self.cmd_SET_THRESHOLD)
        self.gcode.register_command("COLLISION_DETECT_DEBUG", self.cmd_DEBUG)
        self.gcode.register_command("COLLISION_CALIBRATE_START", self.cmd_CALIBRATE_START)
        self.gcode.register_command("COLLISION_CALIBRATE_END", self.cmd_CALIBRATE_END)

        self.printer.register_event_handler("klippy:ready", self._handle_ready)

    def _handle_ready(self):
        self.sensor_obj = self.printer.lookup_object(self.sensor_name, None)
        if self.sensor_obj is None:
            for name, obj in self.printer.objects.items():
                if name.startswith('lis2dw') or name.startswith('adxl345'):
                    self.sensor_obj = obj
                    break
        
        if self.sensor_obj is None:
            raise self.printer.config_error(f"[collision_detect] sensor not found: {self.sensor_name}")

        if hasattr(self.sensor_obj, 'batch_bulk'):
            self.batch_bulk = self.sensor_obj.batch_bulk
        elif hasattr(self.sensor_obj, 'sensor') and hasattr(self.sensor_obj.sensor, 'batch_bulk'):
            self.batch_bulk = self.sensor_obj.sensor.batch_bulk
            
        if self.batch_bulk is None:
            raise self.printer.config_error(f"[collision_detect] the sensor has no batch_bulk controller")

        self.cmd_disable()

    # main callback of the batch processing
    def _handle_sensor_batch(self, msg):
        if not self.is_monitoring:
            # tell BatchBulkHelper that the client has signed off
            return False

        if self.is_handling_trigger:
            return True

        samples = msg.get('data', [])
        if not samples:
            return True

        curtime = self.reactor.monotonic()

        for pt in samples:
            self.sample_counter += 1
            # raw data is in mm/s², convert to m/s² (1 G ≈ 9.80665)
            x = pt[1] / 1000.0
            y = pt[2] / 1000.0
            z = pt[3] / 1000.0
            
            # magnitude of the acceleration
            curr_mag = math.sqrt(x*x + y*y + z*z)

            # first difference at high rate (impact, jerk)
            if self.prev_mag is None:
                self.prev_mag = curr_mag
                impact = 0.0
            else:
                impact = abs(curr_mag - self.prev_mag)
                self.prev_mag = curr_mag

            if self.is_debugging:
                if impact > self.debug_peak:
                    self.debug_peak = impact
                # keep the top samples
                if len(self.debug_samples) < 300:
                    self.debug_samples.append((self.sample_counter, x, y, z, curr_mag, impact))
                elif impact > (self.debug_peak * 0.5):
                    self.debug_samples.pop(0)
                    self.debug_samples.append((self.sample_counter, x, y, z, curr_mag, impact))
                continue

            # warm-up filter at the start
            if (curtime - self.start_time) < self.warmup_time:
                continue

            # collision and stall decision
            if impact >= self.threshold:
                self.consecutive_hits += 1
                if self.consecutive_hits >= self.window_size:
                    self.is_handling_trigger = True
                    peak = impact
                    self.reactor.register_callback(lambda ev: self._execute_interrupt(peak))
                    return True
            else:
                self.consecutive_hits = 0

        # important: return True explicitly to keep the client connected
        return True

    def _debug_timer_tick(self, eventtime):
        if not self.is_debugging:
            return self.reactor.NEVER
        if eventtime >= self.debug_end_time:
            self.cmd_CALIBRATE_END(self.gcode)
            return self.reactor.NEVER
        return eventtime + 0.1

    def _execute_interrupt(self, peak_val):
        curtime = self.reactor.monotonic()
        if (curtime - self.last_trigger_time) < self.cooldown_time:
            self.is_handling_trigger = False
            return
            
        self.last_trigger_time = curtime
        self.cmd_disable()
        
        msg = f"Abnormal collision / stall impact detected: {peak_val:.2f} m/s² ({peak_val/9.80665:.2f} G), set threshold: {self.threshold:.2f} m/s²"
        logging.error(f"[CollisionDetect] {msg}")

        if self.action == 'pause':
            self.gcode.respond_raw(f"!! Collision stopped: {msg}, pausing the print...")
            pause_cmd = self.printer.lookup_object('pause_resume', None)
            if pause_cmd is not None:
                pause_cmd.send_pause_command()
            else:
                self.gcode.run_script_from_command("PAUSE")
            self.is_handling_trigger = False
        else:
            self.printer.invoke_shutdown(
                f"\n{'='*50}\n"
                f"!! [Collision emergency stop triggered] !!\n"
                f"{msg}\n"
                f"Movement interrupted to protect the mechanics!\n"
                f"{'='*50}"
            )

    def cmd_enable(self):
        if self.is_monitoring:
            return
        self.prev_mag = None
        self.consecutive_hits = 0
        self.sample_counter = 0
        self.debug_peak = 0.0
        self.debug_samples = []
        self.start_time = self.reactor.monotonic()
        self.is_handling_trigger = False
        self.is_monitoring = True
        
        # register the callback, this starts batch_bulk._start() by itself
        if self.batch_bulk is not None:
            self.batch_bulk.add_client(self._handle_sensor_batch)

    def cmd_disable(self):
        self.is_monitoring = False
        self.is_debugging = False
        
        if self.debug_timer is not None:
            try:
                self.reactor.unregister_timer(self.debug_timer)
            except Exception:
                pass
            self.debug_timer = None

        if self.batch_bulk is not None:
            if self._handle_sensor_batch in self.batch_bulk.client_cbs:
                self.batch_bulk.client_cbs.remove(self._handle_sensor_batch)
                if not self.batch_bulk.client_cbs:
                    self.batch_bulk._stop()

    def cmd_ENABLE(self, gcmd):
        self.cmd_enable()
        gcmd.respond_info(f"Collision detection enabled (threshold: {self.threshold:.2f} m/s²)")

    def cmd_DISABLE(self, gcmd):
        self.cmd_disable()
        gcmd.respond_info("Collision detection disabled")

    def cmd_SET_THRESHOLD(self, gcmd):
        threshold = gcmd.get_float('THRESHOLD', None)
        window = gcmd.get_int('WINDOW', None)
        action = gcmd.get('ACTION', None)
        if threshold is not None:
            self.threshold = float(threshold)
            gcmd.respond_info(f"Collision threshold set to: {self.threshold:.2f} m/s² ({self.threshold/9.80665:.2f} G)")
        if window is not None:
            self.window_size = int(window)
            gcmd.respond_info(f"Consecutive trigger window set to: {self.window_size}")
        if action is not None:
            self.action = action.lower()
            gcmd.respond_info(f"Trigger action set to: {self.action}")

    def cmd_DEBUG(self, gcmd):
        seconds = gcmd.get_float('SECONDS', 5.0)
        self.cmd_enable()
        self.is_debugging = True
        self.debug_peak = 0.0
        self.sample_counter = 0
        self.debug_samples = []
        self.debug_end_time = self.reactor.monotonic() + seconds
        
        self.debug_timer = self.reactor.register_timer(
            self._debug_timer_tick, self.reactor.monotonic() + 0.1)
            
        gcmd.respond_info(f">>> [High-rate calibration on] for {seconds:.1f} s! Keep shaking or tapping the tool head during this time...")

    def cmd_CALIBRATE_START(self, gcmd):
        self.cmd_enable()
        self.is_debugging = True
        self.debug_peak = 0.0
        self.sample_counter = 0
        self.debug_samples = []
        gcmd.respond_info(">>> Starting the high-rate data capture...")

    def cmd_CALIBRATE_END(self, gcmd):
        if not self.is_debugging:
            gcmd.respond_info("Not in calibration mode")
            return
            
        final_peak = self.debug_peak
        count = self.sample_counter
        collected = list(self.debug_samples)
        
        self.cmd_disable()

        safe_threshold = max(final_peak * 1.3, final_peak + 2.0)

        gcmd.respond_info(
            f"\n{'='*48}\n"
            f"[LIS2DW calibration report] (unit: m/s²)\n"
            f"• High-rate points captured in 5 s: {count}\n"
            f"• Largest impact captured (peak): {final_peak:.2f} m/s² ({final_peak/9.80665:.2f} G)\n"
            f"• ★ Recommended safe collision threshold: {safe_threshold:.2f} m/s² ({safe_threshold/9.80665:.2f} G)\n"
            f"  (suggested setting in printer.cfg, threshold: {safe_threshold:.2f})\n"
            f"{'='*48}"
        )
        
        if collected:
            sorted_samples = sorted(collected, key=lambda x: x[5], reverse=True)[:10]
            lines = ["===== Top 10 largest impacts ====="]
            for s_idx, x, y, z, mag, imp in sorted_samples:
                lines.append(f"#{s_idx:05d} | X:{x:6.2f} Y:{y:6.2f} Z:{z:6.2f} | magnitude:{mag:5.2f} -> impact:{imp:5.2f} m/s²")
            gcmd.respond_info("\n".join(lines))

def load_config(config):
    return CollisionDetect(config)
