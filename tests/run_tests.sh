#!/bin/bash
# Tests for the installer and scripts. Uses fake homes. No sudo, no network, no services.
#   bash tests/run_tests.sh
set -u
if [ -z "${WM_TESTS_IN_COPY:-}" ]; then   # always test a throwaway copy of the repository, never the real folder
    CP="$(mktemp -d)"; cp -a "$(cd "$(dirname "$0")/.." && pwd)/." "$CP/"
    WM_TESTS_IN_COPY=1 bash "$CP/tests/run_tests.sh" "$@"; rc=$?; rm -rf "$CP"; exit $rc
fi
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export WM_KS_ON_PI=1   # F-215 (2.27.0): the installer no longer builds KlipperScreen on the Pi; the older checks below still test that code, the new F-215 checks run without this
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
mkdir -p "$T/fstmp"; export WM_TEST_TMP="$T/fstmp"   # the free-space helper must never see (and erase) the real /tmp, which holds this very copy of the tests
PASS=0; FAIL=0
check() { [ -z "${WM_ONLY:-}" ] || echo "$1" | grep -Eq -- "$WM_ONLY" || return 0   # WM_ONLY=regex runs only the checks whose name matches (to rerun failures)
    if eval "$2" >"$T/.check.out" 2>&1; then PASS=$((PASS+1)); echo "  ok   $1"; else FAIL=$((FAIL+1)); echo "  FAIL $1"; tail -n 6 "$T/.check.out" 2>/dev/null | cut -c1-300 | sed 's/^/        | /'; [ -z "${WM_FAIL_LOG:-}" ] || echo "$1" >> "$WM_FAIL_LOG"; fi; }   # a FAIL shows the last lines the check printed
# Guards (2026-11-25). repo_guard: no test may change the repository copy under test (the installer's own repair step once put factory/ back
# to the last commit in the middle of a run). real_sum: no test may touch the real home of the machine the suite runs on (a panel test once
# re-linked the drivers in ~/klipper/klippy/extras to its throwaway copy, and the real Klipper stopped).
REAL_HOME="${WM_REAL_HOME:-$HOME}"
real_sum() { { find "$REAL_HOME/klipper/klippy/extras" -maxdepth 1 -type l -printf '%f>%l\n' 2>/dev/null | sort; ls "$REAL_HOME/klipper/klippy/extras" 2>/dev/null | wc -l; ls "$REAL_HOME/printer_data/config" 2>/dev/null | grep -v '^backup$' | wc -l; md5sum "$REAL_HOME/printer_data/config/moonraker.conf" 2>/dev/null; } | md5sum | cut -c1-12; }
REAL_SUM0="$(real_sum)"
repo_sum() { git -C "$ROOT" status --porcelain 2>/dev/null | md5sum | cut -c1-12; }
repo_guard() {
    [ -d "$ROOT/.git" ] || return 0
    local s; s="$(repo_sum)"
    if [ -z "${REPO_SUM:-}" ]; then REPO_SUM="$s"
    elif [ "$s" != "$REPO_SUM" ]; then FAIL=$((FAIL+1)); echo "  FAIL a test changed the repository copy, in the section: ${CUR_SEC:-start}"; git -C "$ROOT" status --porcelain | head -n 6 | sed 's/^/        | /'; REPO_SUM="$s"; fi
}
SEC_T0=$(date +%s); : > "$T/.sectimes"
sec() { repo_guard; local n; n=$(date +%s); [ -n "${CUR_SEC:-}" ] && echo "$((n-SEC_T0)) s  $CUR_SEC" >> "$T/.sectimes"; SEC_T0=$n; echo "$1"; CUR_SEC="$1"; }   # the time of each section is listed at the end (to see where the minutes go)

mkstage() {  # make a fake WonderMaker tree and stage folder
    local s="$1" h="$T/src_home"; rm -rf "$h"
    mkdir -p "$h/klipper/klippy/extras" "$h/moonraker/moonraker" "$h/moonraker/scripts" "$h/printer_data/config" "$h/printer_data/systemd" "$h/printer_data/gcodes" "$h/fluidd" "$h/TM_T1/factory_settings"
    echo "[mcu]" > "$h/printer_data/config/printer.cfg"; echo "x" > "$h/printer_data/gcodes/big.gcode"
    echo 'KLIPPER_ARGS="x"' > "$h/printer_data/systemd/klipper.env"; echo "aiohttp" > "$h/moonraker/scripts/moonraker-requirements.txt"
    echo "<html>old</html>" > "$h/fluidd/index.html"; echo '{"a":1}' > "$h/fluidd/config.json"
    mkdir -p "$s"
    tar czf "$s/klipper.tgz" -C "$h" klipper; tar czf "$s/moonraker.tgz" -C "$h" moonraker
    tar czf "$s/data.tgz" -C "$h" --exclude=printer_data/gcodes printer_data fluidd TM_T1
}
mkdir -p "$T/stubpanel"; python3 -c "import zipfile;z=zipfile.ZipFile('$T/stubpanel/fluidd-stub.zip','w');z.writestr('index.html','<html>fluidd panel</html>');z.close()"
inst() { local h="$1"; shift; WM_TEST_PANEL_DIR="${WM_TEST_PANEL_DIR:-$T/stubpanel}" WM_HOME="$h" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" "$@" 2>&1; }

sec "== basics"
check "the suite runs on a committed tree: no uncommitted change in factory/ (the installer's repair step would put it back in this copy)" "[ ! -d $ROOT/.git ] || [ -z \"\$(git -C $ROOT status --porcelain -- factory)\" ]"
check "quick check (tools/quick_check.sh) passes" "bash $ROOT/tools/quick_check.sh"
check "bash syntax installer" "bash -n $ROOT/installer.sh"
check "bash syntax scripts" "for f in $ROOT/scripts/*.sh $ROOT/zr_tools/install_zr_tools.sh; do bash -n \$f || exit 1; done"
check "--version prints" "bash $ROOT/installer.sh --version | grep -q wm_ultra_vanilla_klipper"
check "--help prints" "bash $ROOT/installer.sh --help | grep -q import-settings"
check "unknown option fails" "! bash $ROOT/installer.sh --nope"
check "no Fluidd zip kept in the repo" "[ ! -e $ROOT/fluidd ]"
check "no Claude mention in repo files" "! grep -rIl -i 'claude' $ROOT --exclude-dir=.git --exclude=tests --exclude=run_tests.sh --exclude=*.patch --exclude=*.zip"
check "no private addresses in repo files" "! grep -rIlE '10\.11\.88\.|192\.168\.1\.' $ROOT --exclude-dir=.git --exclude-dir=klipper --exclude-dir=moonraker --exclude=*.patch"
check "both service files can be enabled at boot" "grep -q 'WantedBy=multi-user.target' $ROOT/config/klipper.service && grep -q 'WantedBy=multi-user.target' $ROOT/config/moonraker.service"
check "klipper.service restores saved_variables.cfg before start and backs it up after stop" "grep -q 'ExecStartPre=-.*wm_sv_guard.sh restore' $ROOT/config/klipper.service && grep -q 'ExecStopPost=-.*wm_sv_guard.sh backup' $ROOT/config/klipper.service"
check "wm-sv-guard timer and service files exist" "grep -q 'OnUnitActiveSec=10min' $ROOT/config/wm-sv-guard.timer && grep -q 'wm_sv_guard.sh backup' $ROOT/config/wm-sv-guard.service"

sec "== saved_variables safeguard (wm_sv_guard.sh)"
SG="$T/sg"; mkdir -p "$SG/printer_data/config" "$SG/printer_data/logs"
mksv() { { echo "[Variables]"; echo "box_modify_t0 = 0"; echo "t0_position = (1.0, 2.0)"; for i in $(seq 1 60); do echo "filler_value_$i = $i"; done; } > "$1"; }
sg() { HOME="$SG" bash "$ROOT/scripts/wm_sv_guard.sh" "$@"; }
mksv "$SG/printer_data/config/saved_variables.cfg"
sg backup; check "guard: backup of a healthy file makes the good copy" "cmp -s $SG/printer_data/config/saved_variables.cfg $SG/printer_data/config/saved_variables.cfg.wm-good"
printf '[Variables]\nace_filament_pos = bowden\n' > "$SG/printer_data/config/saved_variables.cfg"
sg backup; check "guard: an unhealthy file never replaces the good copy" "[ \$(stat -c %s $SG/printer_data/config/saved_variables.cfg.wm-good) -gt 1000 ]"
sg restore; check "guard: restore puts the good copy back when the live file is tiny" "[ \$(stat -c %s $SG/printer_data/config/saved_variables.cfg) -gt 1000 ] && grep -q '^t0_position' $SG/printer_data/config/saved_variables.cfg"
check "guard: the bad file is kept next to it" "ls $SG/printer_data/config/saved_variables.cfg.wm-bad-* >/dev/null"
: > "$SG/printer_data/config/saved_variables.cfg"; sg restore; check "guard: restore also works for an empty file" "grep -q '^box_modify_t0 ' $SG/printer_data/config/saved_variables.cfg"
before="\$(md5sum < $SG/printer_data/config/saved_variables.cfg)"; sg restore; check "guard: restore leaves a healthy file alone" "[ \"\$(md5sum < $SG/printer_data/config/saved_variables.cfg)\" = \"$before\" ]"
check "guard: the log has the restore lines" "grep -q RESTORED $SG/printer_data/logs/wm_sv_guard.log"
check "guard: a wrong argument is refused" "! sg nope"

sec "== install from stage folder"
mkstage "$T/stage"; H="$T/h1"; mkdir -p "$H"
OUT="$(inst "$H" --from-stage "$T/stage")"; RC=$?
check "install exits 0" "[ $RC = 0 ]"
check "klippy unpacked" "[ -d $H/klipper/klippy ]"
check "printer.cfg present" "[ -f $H/printer_data/config/printer.cfg ]"
check "gcodes dir created, big gcode not copied" "[ -d $H/printer_data/gcodes ] && [ ! -e $H/printer_data/gcodes/big.gcode ]"
check "panel replaced fluidd" "grep -q -i fluidd $H/fluidd/index.html"
check "fluidd config.json kept" "grep -q '\"a\":1' $H/fluidd/config.json"
check "old fluidd saved" "ls $H/wm-rpi-backup/fluidd-*/index.html"
check "sudo calls recorded" "grep -q 'systemctl enable moonraker' $H/.sudo.log"
check "klipper disabled during install, enabled only at the end" "grep -n 'systemctl disable klipper' $H/.sudo.log | head -1 | cut -d: -f1 | { read a; b=\$(grep -n 'systemctl enable klipper' $H/.sudo.log | head -1 | cut -d: -f1); [ \$a -lt \$b ]; }"
check "can0 rule installed" "grep -q 'install -m 644 .*99-wm-can0.rules' $H/.sudo.log"
check "manifest written" "grep -q 'FILE /etc/systemd/system/moonraker.service' $H/wm-rpi-backup/installed.manifest"

sec "== run again: existing folders are moved, not deleted"
echo "mine" > "$H/printer_data/config/mine.cfg"
inst "$H" --from-stage "$T/stage" >/dev/null
check "previous printer_data saved" "ls $H/wm-rpi-backup/old-*/printer_data/config/mine.cfg"

sec "== without the panel"
H2="$T/h2"; mkdir -p "$H2"; printf 'n\nn\nn\nn\ny\n' > "$T/ans"
WM_HOME="$H2" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --from-stage "$T/stage" < "$T/ans" >/dev/null 2>&1
check "panel declined: old fluidd kept" "grep -q old $H2/fluidd/index.html"

sec "== touchscreen"
H3="$T/h3"; mkdir -p "$H3"
WM_TEST_SCREEN=1024x600 WM_TEST_TOUCH=1 inst "$H3" --from-stage "$T/stage" > "$T/scr.out"
check "screen: panel files in KlipperScreen" "[ -f $H3/KlipperScreen/panels/zr_tools.py ] && [ -f $H3/KlipperScreen/panels/zr_views.py ] && [ -f $H3/KlipperScreen/panels/zr_logic.py ]"
check "screen: the Unlock gripper icon is made for every KlipperScreen theme (valid SVG, same colour as the lock icon, run twice = same)" "U=\$(mktemp -d); mkdir -p \$U/styles/material-dark/images \$U/styles/z-bolt/images; printf '<svg xmlns=\"http://www.w3.org/2000/svg\"><path style=\"fill:#e2e2e2;fill-opacity:1\" d=\"M0 0\"/></svg>' > \$U/styles/material-dark/images/lock.svg; printf '<svg xmlns=\"http://www.w3.org/2000/svg\"><rect style=\"fill:none;stroke:#ffffff;stroke-width:3\"/></svg>' > \$U/styles/z-bolt/images/lock.svg; python3 $ROOT/zr_tools/make_unlock_icon.py \$U | grep -q '2 theme' && grep -q '#e2e2e2' \$U/styles/material-dark/images/unlock.svg && grep -q 'stroke:#ffffff' \$U/styles/z-bolt/images/unlock.svg && python3 -c \"import xml.dom.minidom as m,sys;[m.parse(sys.argv[1]+'/styles/'+t+'/images/unlock.svg') for t in ('material-dark','z-bolt')]\" \$U && python3 $ROOT/zr_tools/make_unlock_icon.py \$U | grep -q '0 theme' && grep -q make_unlock_icon $ROOT/installer.sh && grep -q make_unlock_icon $ROOT/zr_tools/install_zr_tools.sh"
check "screen bundle: the small download (screen_board_bundle) is up to date with the files it holds (rebuild: bash scripts/make_screen_bundle.sh)" "bash $ROOT/scripts/make_screen_bundle.sh --check >/dev/null"
check "screen bundle: small (under 1 MB) and holds every file screen_board.sh reads from its own folder" "B=\$(mktemp -d); tar xzf $ROOT/screen_board_bundle/wm-screen-board.tar.gz -C \$B && [ \$(wc -c < $ROOT/screen_board_bundle/wm-screen-board.tar.gz) -lt 1048576 ] && for f in \$(grep -oE 'REPO_DIR\}?/[A-Za-z0-9_./-]+' $ROOT/scripts/screen_board.sh | sed 's#^REPO_DIR}\?/##' | grep -E '^(zr_tools|screen_rescue|config|VERSION|scripts)' | grep -v '/\$' | sort -u); do [ -e \$B/\$f ] || { echo missing \$f; rm -rf \$B; exit 1; }; done; for f in scripts/screen_board.sh scripts/lib_free_space.sh scripts/screen_board_inspect.sh scripts/screen_board_precheck.sh; do [ -f \$B/\$f ] || exit 1; done; rm -rf \$B"
check "screen: default layout tabs" "grep -q 'layout = tabs' $H3/printer_data/config/zr_screen.conf"
check "screen: default size is comfortable" "grep -q 'density = comfortable' $H3/printer_data/config/zr_screen.conf"
check "screen: macros included in printer.cfg" "grep -q 'include zr_tools.cfg' $H3/printer_data/config/printer.cfg && [ -f $H3/printer_data/config/zr_tools.cfg ]"
check "screen: KlipperScreen installed with x11" "grep -q 'KlipperScreen-install backend=x11' $H3/.sudo.log"
check "screen: pinned commit used" "grep -q 'fetch .*KlipperScreen @ 34610ceae31e12a10cc980e20a1dec9976f97dd4' $H3/.sudo.log"
check "screen: service enabled" "grep -q 'systemctl enable KlipperScreen' $H3/.sudo.log"
check "screen: answers saved" "grep -q WANT_SCREEN=1 $H3/wm-rpi-backup/install.conf && grep -q REPO_DIR= $H3/wm-rpi-backup/install.conf"
check "screen: found screen reported" "grep -q 'Screen found: 1024x600' $T/scr.out"
inst "$H3" --screen-layout grid >/dev/null; check "screen-layout grid rewrites the file" "grep -q 'layout = grid' $H3/printer_data/config/zr_screen.conf"
rm -f "$H3/KlipperScreen/panels/zr_views.py"; inst "$H3" --repair >/dev/null
check "repair puts the panel files back" "[ -f $H3/KlipperScreen/panels/zr_views.py ]"
rm -f "$H3/KlipperScreen/panels/zr_logic.py"; printf 'n\nn\nn\nn\n' | WM_HOME="$H3" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --doctor > "$T/doc.out" 2>&1
check "doctor notices missing panel file" "grep -q 'ZR Tools panel files are missing' $T/doc.out"
H5="$T/h5"; mkdir -p "$H5"; inst "$H5" --from-stage "$T/stage" --screen off >/dev/null
check "screen off: nothing installed" "[ ! -d $H5/KlipperScreen ] && grep -q WANT_SCREEN=0 $H5/wm-rpi-backup/install.conf"
H6="$T/h6"; mkdir -p "$H6"; inst "$H6" --from-stage "$T/stage" --screen on --screen-layout grid >/dev/null
check "options: grid layout" "grep -q 'layout = grid' $H6/printer_data/config/zr_screen.conf"
H7="$T/h7"; mkdir -p "$H7"; inst "$H7" --from-stage "$T/stage" --screen macros >/dev/null
check "screen macros: only the macros, no KlipperScreen" "[ ! -d $H7/KlipperScreen ] && ! grep -q 'KlipperScreen-install' $H7/.sudo.log && [ -f $H7/printer_data/config/zr_tools.cfg ] && grep -q '^\\[include zr_tools.cfg\\]' $H7/printer_data/config/printer.cfg && grep -q WANT_SCREEN=macros $H7/wm-rpi-backup/install.conf"
check "nginx step lets nginx reach the home folder (Fluidd 403 fix)" "grep -q 'chmod o+x' $H7/.sudo.log"
check "polkit rule step runs (Fluidd PolKit warning fix)" "grep -q 'polkit rules' $H7/.sudo.log"
check "screen: bad value fails" "! bash $ROOT/installer.sh --screen maybe"
check "--screen-test is read-only" "WM_TEST_SCREEN=800x480 WM_TEST_TOUCH=0 bash $ROOT/installer.sh --screen-test | grep -q 'compact'"
sec "== gcode shell command extension"
check "bundled gcode_shell_command.py compiles and registers RUN_SHELL_COMMAND" "python3 -m py_compile $ROOT/config/gcode_shell_command.py && grep -q RUN_SHELL_COMMAND $ROOT/config/gcode_shell_command.py"
check "--shell-command needs on or off" "! bash $ROOT/installer.sh --shell-command maybe"
mkstage "$T/stage_sc"; HS="$T/hs"; mkdir -p "$HS"
OUT="$(inst "$HS" --from-stage "$T/stage_sc" --screen off)"
check "shell command is installed by default, with no question" "cmp -s $ROOT/config/gcode_shell_command.py $HS/klipper/klippy/extras/gcode_shell_command.py"
check "the shell command install asks no question" "! echo \"$OUT\" | grep -qi 'Install the Klipper gcode shell'"
rm -f "$HS/klipper/klippy/extras/gcode_shell_command.py"
OUT="$(inst "$HS" --update --shell-command on)"
check "--update --shell-command on installs it" "cmp -s $ROOT/config/gcode_shell_command.py $HS/klipper/klippy/extras/gcode_shell_command.py"
printf 'y\n' | WM_HOME="$HS" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --uninstall >/dev/null 2>&1
check "--uninstall removes the shell command extension" "grep -q 'rm -f .*extras/gcode_shell_command.py' $HS/.sudo.log"
rm -f "$HS/wm-rpi-backup/"*.removed-* 2>/dev/null; OUT="$(inst "$HS" --update --shell-command on)"
check "the choice is saved for later updates" "grep -rq 'WANT_SHELLCMD=1' $HS --include='*.conf' --include='*answers*' 2>/dev/null || grep -rq 'WANT_SHELLCMD=1' $HS 2>/dev/null"
echo "# local edit" >> "$HS/klipper/klippy/extras/gcode_shell_command.py"
OUT="$(inst "$HS" --update)"
check "a plain --update puts the extension back (choice remembered)" "cmp -s $ROOT/config/gcode_shell_command.py $HS/klipper/klippy/extras/gcode_shell_command.py"
mkdir -p "$HS/klipper/klippy/extras"; echo "old copy" > "$HS/klipper/klippy/extras/wm_mcu_tweaks.py"; echo "mine" > "$HS/klipper/klippy/extras/my_own_module.py"
OUT="$(inst "$HS" --update)"
check "--update replaces a changed Pi-side module (wm_mcu_tweaks.py) with the repository copy" "cmp -s $ROOT/factory/ultra/klipper/klippy/extras/wm_mcu_tweaks.py $HS/klipper/klippy/extras/wm_mcu_tweaks.py && echo \"$OUT\" | grep -q 'updated wm_mcu_tweaks.py'"
check "--update leaves files that are not wm_*.py alone" "grep -q mine $HS/klipper/klippy/extras/my_own_module.py"
OUT="$(inst "$HS" --update)"
check "a second --update has nothing to copy" "echo \"$OUT\" | grep -q 'Pi-side modules are already the latest' && ! echo \"$OUT\" | grep -q 'updated wm_mcu_tweaks.py'"
OUT="$(inst "$HS" --update --shell-command off)"
check "--shell-command off leaves the file alone and is remembered" "grep -rq 'WANT_SHELLCMD=0' $HS 2>/dev/null"
check "--help mentions --shell-command" "bash $ROOT/installer.sh --help | grep -q shell-command"

sec "== remote access add-ons (Obico, OctoApp, OctoEverywhere)"
check "--obico needs on or off" "! bash $ROOT/installer.sh --obico maybe"
check "--octoapp needs on or off" "! bash $ROOT/installer.sh --octoapp maybe"
check "--octoeverywhere needs on or off" "! bash $ROOT/installer.sh --octoeverywhere maybe"
mkstage "$T/stage_r"; HR="$T/hr"; mkdir -p "$HR"
OUT="$(inst "$HR" --from-stage "$T/stage_r" --screen off)"
check "none of the three is installed unless asked for" "[ ! -e $HR/octoapp ] && [ ! -e $HR/octoeverywhere ] && [ ! -e $HR/moonraker-obico ]"
printf '[server]\nport: 7125\n[authorization]\ntrusted_clients:\n    127.0.0.0/8\n' > "$HR/printer_data/config/moonraker.conf"
OUT="$(inst "$HR" --update --obico on --octoapp on --octoeverywhere on)"
check "--update --obico on downloads and installs Obico against this Moonraker" "[ -d $HR/moonraker-obico ] && grep -q 'obico install.sh' $HR/.sudo.log"
check "OctoApp is pointed at moonraker.conf and moonraker.service" "[ -d $HR/octoapp ] && grep -q 'octoapp install.sh $HR/printer_data/config/moonraker.conf moonraker.service' $HR/.sudo.log"
check "OctoEverywhere is pointed at moonraker.conf and moonraker.service" "[ -d $HR/octoeverywhere ] && grep -q 'octoeverywhere install.sh $HR/printer_data/config/moonraker.conf moonraker.service' $HR/.sudo.log"
check "the linking step is left to the user and explained" "grep -q 'cd ~/moonraker-obico && ./install.sh' $ROOT/installer.sh"
check "the choices are saved" "grep -rq 'WANT_OBICO=1' $HR && grep -rq 'WANT_OCTOAPP=1' $HR && grep -rq 'WANT_OCTOEVERYWHERE=1' $HR"
: > "$HR/.sudo.log"; OUT="$(inst "$HR" --update)"
check "a plain --update does not run the makers' installers again" "! grep -q 'install.sh' $HR/.sudo.log && echo \"$OUT\" | grep -q 'already installed'"
OUT="$(inst "$HR" --doctor)"
check "--doctor sees the add-ons" "echo \"$OUT\" | grep -q 'Obico is downloaded' && echo \"$OUT\" | grep -q 'OctoApp is downloaded'"
rm -rf "$HR/octoapp"; OUT="$(inst "$HR" --doctor)"
check "--doctor reports a missing add-on" "echo \"$OUT\" | grep -q 'OctoApp is missing'"
OUT="$(printf 'y\n' | WM_HOME="$HR" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --uninstall 2>&1)"
check "--uninstall leaves the add-ons and says how to remove them" "[ -d $HR/moonraker-obico ] && echo \"$OUT\" | grep -q 'NOT removed'"
check "the maker installers' own repos are the ones used" "grep -q 'TheSpaghettiDetective/moonraker-obico' $ROOT/installer.sh && grep -q 'crysxd/OctoApp-Plugin' $ROOT/installer.sh && grep -q 'QuinnDamerell/OctoPrint-OctoEverywhere' $ROOT/installer.sh"

sec "== menu and --remove"
M() { printf "$1" | WM_TEST_NO_FETCH=1 WM_HOME="$2" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" "${@:3}" 2>&1; }
check "--menu on a home with no install says not installed" "mkdir -p $T/mempty && M '0\n' $T/mempty --menu | grep -q 'Not installed yet'"
check "--menu shows every section" "M '0\n' $HR --menu | grep -q 'Install or reinstall' && M '0\n' $HR --menu | grep -q 'Backup and restore' && M '0\n' $HR --menu | grep -q 'Add-ons'"
check "--menu shows the version and service status" "M '0\n' $HR --menu | grep -q 'Klipper:' && M '0\n' $HR --menu | grep -q 'installer 2\\.'"
check "menu: exit with 0, and at end of input" "M '0\n' $HR --menu >/dev/null && M '' $HR --menu >/dev/null"
check "menu: a wrong choice is explained, not fatal" "M 'x\n9\n0\n' $HR --menu | grep -c 'Choose a number' | grep -q 2"
check "menu: add-ons page lists status of each add-on" "M '3\n0\n0\n' $HR --menu | grep -q 'Obico for Klipper.*installed' && M '3\n0\n0\n' $HR --menu | grep -q 'OctoEverywhere' && M '3\n0\n0\n' $HR --menu | grep -q 'gcode shell command'"
check "menu: check-and-fix runs the doctor" "M '4\n1\n0\n0\n' $HR --menu | grep -q 'Doctor\\|doctor\\|Check'"
check "menu: there is no touchscreen settings page any more" "! M '0\n' $HR --menu | grep -q 'Touchscreen settings'"
check "menu: Uninstall section lists everything that can be removed" "M '6\n0\n0\n' $HR --menu | grep -q 'Fluidd web page' && M '6\n0\n0\n' $HR --menu | grep -q 'Moonraker' && M '6\n0\n0\n' $HR --menu | grep -q 'My printer data' && M '6\n0\n0\n' $HR --menu | grep -q 'All programs'"
check "menu warns when KIAUH is on the Pi" "mkdir -p $HR/kiauh && M '0\n' $HR --menu | grep -q 'KIAUH'; rmdir $HR/kiauh"
check "menu: nothing is installed by merely opening and leaving it" "[ ! -e $HR/.menu-touched ]"
check "menu shows a print in progress" "WM_TEST_PRINT_STATE=printing M '0\n' $HR --menu | grep -q 'print is active'"
check "--install is accepted (skips the menu)" "bash $ROOT/installer.sh --help | grep -q -- '--install'"
check "--remove needs a known name" "! M 'y\n' $HR --remove nothing"
check "--remove asks first and keeps everything on no" "M 'n\n' $HR --remove obico | grep -q 'Nothing changed' && [ -d $HR/moonraker-obico ]"
check "--remove obico removes its folder and is remembered" "M 'y\n' $HR --remove obico | grep -q 'removed' && [ ! -e $HR/moonraker-obico ] && grep -q 'WANT_OBICO=0' $HR/wm-rpi-backup/install.conf"
inst "$HR" --update --shell-command on >/dev/null
mkdir -p "$HR/printer_data/config"; printf '[gcode_shell_command hi]\ncommand: echo hi\n' > "$HR/printer_data/config/x.cfg"
check "--remove shell-command refuses while printer.cfg still uses it" "! M 'y\n' $HR --remove shell-command"
rm -f "$HR/printer_data/config/x.cfg"
check "--remove shell-command removes the file" "M 'y\n' $HR --remove shell-command | grep -q 'Removed' && [ ! -e $HR/klipper/klippy/extras/gcode_shell_command.py ]"
check "--webcam off is accepted with --update" "inst $HR --update --webcam off | grep -q 'Update finished'"


sec "== PolKit warning (PackageKit)"
: > "$HR/.sudo.log"; rm -f "$HR/.polkit_fixed"
OUT="$(WM_TEST_POLKIT_WARN=1 M '0\n' $HR --menu)"
check "menu open: Moonraker's PolKit warning is detected and fixed" "echo \"$OUT\" | grep -q 'PolKit warning fixed' && grep -q 'apt-get install -y packagekit' $HR/.sudo.log && grep -q 'systemctl restart moonraker' $HR/.sudo.log"
: > "$HR/.sudo.log"
check "menu open: nothing is done when Moonraker reports nothing" "M '0\n' $HR --menu >/dev/null; ! grep -q packagekit $HR/.sudo.log"
rm -f "$HR/.polkit_fixed"; : > "$HR/.sudo.log"
OUT="$(WM_TEST_POLKIT_WARN=1 WM_TEST_PRINT_STATE=printing M '0\n' $HR --menu)"
check "menu open: during a print the warning is only mentioned" "echo \"$OUT\" | grep -q 'next time you open the menu' && ! grep -q packagekit $HR/.sudo.log"
rm -f "$HR/.polkit_fixed"; : > "$HR/.sudo.log"
check "PackageKit missing (even before Moonraker complains) is fixed" "WM_TEST_PACKAGEKIT=0 M '0\n' $HR --menu | grep -q 'PolKit warning fixed' && grep -q 'apt-get install -y packagekit' $HR/.sudo.log"
rm -f "$HR/.polkit_fixed"
OUT="$(WM_TEST_POLKIT_WARN=1 inst "$HR" --doctor)"
check "--doctor reports the PolKit warning and fixes it" "echo \"$OUT\" | grep -q 'PolKit warnings detected' && [ -f $HR/.polkit_fixed ]"
rm -f "$HR/.polkit_fixed"; : > "$HR/.sudo.log"
WM_TEST_POLKIT_WARN=1 inst "$HR" --repair >/dev/null
check "--repair installs PackageKit through the PolicyKit step" "grep -q 'apt-get install -y packagekit' $HR/.sudo.log"
rm -f "$HR/.polkit_fixed"
check "--check mentions it without changing anything" "WM_TEST_POLKIT_WARN=1 M '' $HR --check | grep -q 'PolKit' && [ ! -f $HR/.polkit_fixed ]"
check "install and update end with the PolKit look" "grep -q 'polkit_check_and_fix' $ROOT/installer.sh && sed -n '/^self_test()/,/^}/p' $ROOT/installer.sh | grep -q polkit_check_and_fix"

sec "== restore from a numbered list"
RS="$T/rs"; mkdir -p "$RS"; mkstage "$T/stage_rs"; inst "$RS" --from-stage "$T/stage_rs" --screen off >/dev/null
M '' "$RS" --backup >/dev/null; sleep 1; M '' "$RS" --backup >/dev/null
OUT="$(M '5\n2\n0\n0\n0\n' $RS --menu)"
check "restore page shows the folder and numbers the backups" "echo \"$OUT\" | grep -q 'kept in: .*ultra-backup/settings' && echo \"$OUT\" | grep -q '1) wm-backup-' && echo \"$OUT\" | grep -q '2) wm-backup-'"
check "restore page offers a file in another place" "echo \"$OUT\" | grep -q 'another place'"
check "choosing a number restores that backup" "M '5\n2\n1\ny\n0\n0\n' $RS --menu | grep -q 'Restored from .*wm-backup-'"
check "an unknown number is explained" "M '5\n2\n99\n0\n0\n' $RS --menu | grep -q 'Choose a number from the list'"
check "with no backups the page says so" "mkdir -p $T/rs0 && cp -a $RS/. $T/rs0/ && rm -rf $T/rs0/ultra-backup/settings && M '5\n2\n0\n0\n' $T/rs0 --menu | grep -q 'no backups in that folder'"

sec "== uninstall section (--remove)"
mkun() { local h="$1"; rm -rf "$h"; mkdir -p "$h"; mkstage "$T/stage_un"; inst "$h" --from-stage "$T/stage_un" --screen off --webcam on --timelapse on >/dev/null; printf '[server]\nport: 7125\n\n[timelapse]\noutput_path: ~/printer_data/timelapse\n\n[update_manager]\n' > "$h/printer_data/config/moonraker.conf"; }
UN="$T/un"; mkun "$UN"
check "uninstall: webcam asks first" "M 'n\n' $UN --remove webcam | grep -q 'Nothing changed' && [ -d $UN/crowsnest ]"
check "uninstall: webcam is removed and remembered" "M 'y\n' $UN --remove webcam | grep -q 'Webcam service removed' && [ ! -e $UN/crowsnest ] && grep -q 'systemctl stop crowsnest' $UN/.sudo.log && grep -q 'WANT_CROWSNEST=0' $UN/wm-rpi-backup/install.conf"
check "uninstall: timelapse is removed, [timelapse] commented out, copy kept" "M 'y\n' $UN --remove timelapse | grep -q 'Timelapse removed' && [ ! -e $UN/moonraker-timelapse ] && grep -q '^#\[timelapse\]' $UN/printer_data/config/moonraker.conf && grep -q '^#output_path' $UN/printer_data/config/moonraker.conf && grep -q '^\[update_manager\]' $UN/printer_data/config/moonraker.conf && ls $UN/printer_data/config/moonraker.conf.wm-before-timelapse-removal-*"
check "uninstall: Fluidd web page and nginx site" "M 'y\n' $UN --remove fluidd | grep -q 'Fluidd web page removed' && [ ! -e $UN/fluidd ] && grep -q 'rm -f /etc/nginx/sites-enabled/fluidd' $UN/.sudo.log"
check "uninstall: Moonraker" "M 'y\n' $UN --remove moonraker | grep -q 'moonraker removed' && [ ! -e $UN/moonraker ] && [ -d $UN/printer_data ] && grep -q 'rm -f /etc/systemd/system/moonraker.service' $UN/.sudo.log"
check "uninstall: Klipper" "M 'y\n' $UN --remove klipper | grep -q 'klipper removed' && [ ! -e $UN/klipper ] && [ -d $UN/printer_data ]"
check "uninstall: printer data needs the word DELETE" "M 'y\nno\n' $UN --remove data | grep -q 'Nothing changed' && [ -d $UN/printer_data ]"
check "uninstall: printer data (and TM_T1) is backed up, then deleted" "M 'y\nDELETE\n' $UN --remove data | grep -q 'Printer data deleted' && [ ! -e $UN/printer_data ] && [ ! -e $UN/TM_T1 ] && ls $UN/ultra-backup/settings/wm-backup-*.tgz"
check "uninstall: a name that is not installed is said so, not an error" "M '' $UN --remove klipper | grep -q 'not installed'"
UA="$T/ua"; mkun "$UA"
check "uninstall everything: wrong word changes nothing" "M 'nope\n' $UA --remove all | grep -q 'Nothing changed' && [ -d $UA/klipper ]"
mkdir -p "$UA/crowsnest-env" "$UA/wm-stage"; echo x > "$UA/octoapp-installer.log"
check "uninstall everything: shows what will be removed before asking, and removes nothing on a wrong word" "M 'nope\n' $UA --remove all | grep -q 'This is what will be removed' && M 'nope\n' $UA --remove all | grep -q -- '- fluidd'"
OUT="$(M 'REMOVE\n' $UA --remove all)"
check "uninstall everything: shows a progress bar that ends at 100 percent" "echo \"$OUT\" | grep -q 'Removing .* (step 1 of ' && echo \"$OUT\" | grep -q '100%  Done'"
check "uninstall everything: lists what is still on the Pi and how to remove it" "echo \"$OUT\" | grep -q 'Still on this Pi' && echo \"$OUT\" | grep -q 'wm-stage' && echo \"$OUT\" | grep -q 'printer_data'"
check "uninstall everything: removes the crowsnest environment too" "[ ! -e $UA/crowsnest-env ]"
check "uninstall everything: removes programs, keeps printer data and backups" "echo \"$OUT\" | grep -q 'programs were removed' && [ ! -e $UA/klipper ] && [ ! -e $UA/moonraker ] && [ ! -e $UA/fluidd ] && [ ! -e $UA/crowsnest ] && [ -d $UA/printer_data/config ] && [ -d $UA/wm-rpi-backup ]"
EX="$T/ex"; mkun "$EX"; M '' "$EX" --backup >/dev/null; echo x > "$EX/wm-support-1.tgz"; mkdir -p "$EX/wm-stage"; mkdir -p "$EX/wm-rpi-backup"; echo dhcpcd-was-enabled > "$EX/wm-rpi-backup/netmgr.state"; : > "$EX/.sudo.log"
check "erase: lists everything, says nothing is kept but the installer folder, and no backup is made" "M 'nope\n' $EX --remove erase | grep -q 'ERASE EVERYTHING' && M 'nope\n' $EX --remove erase | grep -q 'NO backup is made' && M 'nope\n' $EX --remove erase | grep -q 'Kept: the installer folder'"
check "erase: a wrong word changes nothing" "M 'nope\n' $EX --remove erase | grep -q 'Nothing changed' && [ -d $EX/klipper ] && [ -d $EX/printer_data ]"
OUT="$(M 'ERASE\n' $EX --remove erase)"
check "erase: shows a progress bar that ends at 100 percent" "echo \"$OUT\" | grep -q 'Removing .* (step 1 of ' && echo \"$OUT\" | grep -q '100%  Done'"
check "erase: removes programs, printer data, TM_T1, backups, bundles, the old-board copy and the records" "echo \"$OUT\" | grep -q 'Everything was erased' && for d in klipper moonraker fluidd crowsnest printer_data TM_T1 ultra-backup/settings wm-stage wm-rpi-backup wm-support-1.tgz; do [ ! -e $EX/\$d ] || { echo left \$d; exit 1; }; done"
check "erase: switches NetworkManager back (it was switched by the installer)" "grep -q 'systemctl enable dhcpcd' $EX/.sudo.log"
check "erase: keeps the installer folder" "[ -f $ROOT/installer.sh ]"
check "menu: the Uninstall page has All programs and Erase everything" "M '6\n0\n0\n' $EX --menu | grep -q 'All programs' && M '6\n0\n0\n' $EX --menu | grep -q 'Erase everything'"
check "uninstall: --help lists every name" "bash $ROOT/installer.sh --help | grep -q 'octoeverywhere, fluidd, moonraker, klipper, data, system'"


sec "== start Klipper again, and clean up installer files"
check "menu: Advanced has Start Klipper again" "M '7\n0\n0\n' $HR --menu | grep -q 'Start Klipper again'"
: > "$HR/.sudo.log"
check "menu: Start Klipper again enables it at boot and starts it" "M '7\n2\n0\n0\n' $HR --menu | grep -q 'Klipper enabled and started' && grep -q 'systemctl enable klipper' $HR/.sudo.log && grep -q 'systemctl restart klipper' $HR/.sudo.log"
check "--start-klipper is accepted on the command line" "M '' $HR --start-klipper | grep -q 'Start Klipper again'"
check "--start-klipper is refused during a print" "! WM_TEST_PRINT_STATE=printing M '' $HR --start-klipper"
CU="$T/cu"; mkun "$CU"; M '' "$CU" --backup >/dev/null; echo x > "$CU/wm-support-1.tgz"; echo x > "$CU/printer_data/config/printer.cfg.wm-model-bak"
check "uninstall menu lists the clean-up page" "M '6\n0\n0\n' $CU --menu | grep -q 'Clean up installer files'"
OUT="$(M '0\n' $CU --remove cleanup)"
check "clean-up page lists each group with its size" "echo \"$OUT\" | grep -q 'Settings backups.*item' && echo \"$OUT\" | grep -q 'Support bundles.*item' && echo \"$OUT\" | grep -q 'Config safety copies' && echo \"$OUT\" | grep -q 'installer folder itself'"
check "clean-up page never lists printer data" "! echo \"$OUT\" | grep -q 'Delete my printer data'"
check "clean-up: support bundles after y" "M '2\ny\n0\n' $CU --remove cleanup | grep -q 'Deleted: Support bundles' && [ ! -e $CU/wm-support-1.tgz ]"
check "clean-up: config safety copies after y" "M '7\ny\n0\n' $CU --remove cleanup | grep -q 'Deleted: Config safety' && [ ! -e $CU/printer_data/config/printer.cfg.wm-model-bak ] && [ -f $CU/printer_data/config/printer.cfg ]"
check "clean-up: backups need the word DELETE" "M '1\nno\n0\n' $CU --remove cleanup | grep -q 'Nothing changed' && ls $CU/ultra-backup/settings/wm-backup-*.tgz"
check "clean-up: backups deleted after DELETE" "M '1\nDELETE\n0\n' $CU --remove cleanup | grep -q 'Deleted: Settings backups' && [ ! -e $CU/ultra-backup/settings ]"
check "clean-up: nothing-to-delete groups say so" "M '1\n0\n' $CU --remove cleanup | grep -q 'Nothing to delete'"
OUT="$(M '9\nDELETE\n0\n' $CU --remove cleanup)"
check "clean-up: installer records need DELETE and leave printer data" "echo \"$OUT\" | grep -q 'Update and the menu will say so' && [ ! -e $CU/wm-rpi-backup ] && [ -d $CU/printer_data/config ]"
RC="$T/repocopy"; rm -rf "$RC"; cp -a "$ROOT" "$RC"
check "clean-up: the installer folder is deleted only after DELETE (on a copy)" "printf '10\nnope\n0\n' | WM_HOME=$CU WM_INSTALLER_TEST=1 bash $RC/installer.sh --remove cleanup >/dev/null 2>&1; [ -f $RC/installer.sh ] && printf '10\nDELETE\n' | WM_HOME=$CU WM_INSTALLER_TEST=1 bash $RC/installer.sh --remove cleanup | grep -q 'installer folder was deleted' && [ ! -e $RC ]"
check "clean-up: --help lists it" "bash $ROOT/installer.sh --help | grep -q 'cleanup (installer files'"

sec "== plan lists every optional program"
PO="$T/plan"; mkdir -p "$PO"; mkstage "$T/stage_plan"
OUT="$(WM_TEST_PANEL_DIR=$T/stubpanel WM_HOME=$PO WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --dry-run --from-stage $T/stage_plan --model ultra-s --obico on --octoapp on --octoeverywhere off --screen off 2>&1 </dev/null)"
check "plan names obico, octoapp and octoeverywhere with their answers" "echo \"$OUT\" | grep -q 'obico  *yes' && echo \"$OUT\" | grep -q 'octoapp  *yes' && echo \"$OUT\" | grep -q 'octoeverywhere  *no'"
check "plan names every other optional program" "for n in 'panel (Fluidd)' webcam timelapse 'shell command' touchscreen; do echo \"$OUT\" | grep -q \"\$n\" || exit 1; done"
check "every saved WANT_ answer is in the plan list (add new programs to PLAN_OPTIONS; WANT_NETMGR is kept only so old saved answers still load, F-234)" "for v in \$(sed -n '/^save_answers()/,/^}/p' $ROOT/installer.sh | grep -o 'WANT_[A-Z]*' | sort -u | grep -v WANT_NETMGR); do grep -q \"|\$v\\\"\" $ROOT/installer.sh || { echo missing \$v; exit 1; }; done"


sec "== 2.27.0 (F-215): KlipperScreen only on the screen board"
inst2() { local h="$1"; shift; env -u WM_KS_ON_PI WM_TEST_PANEL_DIR="${WM_TEST_PANEL_DIR:-$T/stubpanel}" WM_HOME="$h" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" "$@" 2>&1; }
F5="$T/f215a"; rm -rf "$F5"; mkdir -p "$F5"; mkstage "$T/stage_f215"
OUT="$(inst2 "$F5" --from-stage "$T/stage_f215" --screen on)"
check "F-215: --screen on says KlipperScreen is no longer installed on the Pi, installs the ZR Tools macros and puts no KlipperScreen on the Pi" "echo \"\$OUT\" | grep -q 'no longer installed on the Pi' && [ ! -d $F5/KlipperScreen ] && grep -q 'WANT_SCREEN=macros' $F5/wm-rpi-backup/install.conf"
F6="$T/f215b"; rm -rf "$F6"; mkdir -p "$F6"
inst "$F6" --from-stage "$T/stage_f215" --screen on >/dev/null
check "F-215: (setup for the next check) the old install put KlipperScreen on the Pi" "[ -d $F6/KlipperScreen ] || grep -q 'WANT_SCREEN=1' $F6/wm-rpi-backup/install.conf"
printf '[main]\n' > $F6/printer_data/config/KlipperScreen.conf
OUT="$(inst2 "$F6" --update)"
check "F-215: the update removes a KlipperScreen on the Pi by itself, no question, copies its settings file first, and remembers macros" "echo \"\$OUT\" | grep -q 'no longer installed on the Pi' && [ ! -d $F6/KlipperScreen ] && ls $F6/wm-rpi-backup/KlipperScreen.conf.before-removal-* >/dev/null 2>&1 && grep -q 'WANT_SCREEN=macros' $F6/wm-rpi-backup/install.conf"
check "F-215: --screen-board needs user@address" "! WM_INSTALLER_TEST=1 WM_HOME=$F5 bash $ROOT/installer.sh --screen-board nohost >/dev/null 2>&1"
OUT="$(WM_INSTALLER_TEST=1 WM_HOME=$F5 WM_ASSUME_YES=1 bash $ROOT/installer.sh --dry-run --screen-board t13dp@10.0.0.9 2>&1 </dev/null)"
check "F-215: --screen-board --dry-run shows what would run on the board, does not add the board and installs nothing" "echo \"\$OUT\" | grep -q 'would add the board t13dp@10.0.0.9' && ! echo \"\$OUT\" | grep -q 'Board t13dp@10.0.0.9 added' && [ ! -s $F5/.ssh/id_ed25519 ]"
check "F-215: the install no longer asks for a touchscreen on the Pi" "[ \$(grep -c 'Add a touchscreen (KlipperScreen with the ZR Tools page) on this Pi' $ROOT/installer.sh) = 1 ] && grep -B2 'Add a touchscreen (KlipperScreen with the ZR Tools page) on this Pi' $ROOT/installer.sh | grep -q 'WM_KS_ON_PI' && grep -q 'Set up the touchscreen board now' $ROOT/installer.sh"
# B-083: the board restarts at the end of its install and the ssh connection closes with an error code: that is a finished install
FS="$T/fakessh"; printf '#!/bin/bash\necho "Rebooting in 10 seconds (Ctrl+C cancels)."\nexit 255\n' > "$FS.ok"; printf '#!/bin/bash\necho "E: could not download"\nexit 255\n' > "$FS.bad"; chmod +x "$FS.ok" "$FS.bad"
F6="$T/f215b"; rm -rf "$F6"; mkdir -p "$F6"
OUT="$(WM_SSH="$FS.ok" WM_INSTALLER_TEST=1 WM_HOME=$F6 WM_ASSUME_YES=1 bash $ROOT/installer.sh --screen-board t13dp@10.0.0.9 2>&1 </dev/null)"; RC=$?
check "B-083: --screen-board counts a board that restarted at the end as set up (no 'did not finish')" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'The screen board t13dp@10.0.0.9 is set up' && ! echo \"\$OUT\" | grep -q 'did not finish'"
OUT="$(WM_SSH="$FS.bad" WM_INSTALLER_TEST=1 WM_HOME=$F6 WM_ASSUME_YES=1 bash $ROOT/installer.sh --screen-board t13dp@10.0.0.9 2>&1 </dev/null)"; RC=$?
check "B-083: --screen-board still says 'did not finish' when the board install really stopped" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'did not finish'"
# B-084: a board install keeps an existing KlipperScreen.conf (own menu entries, [main], the settings saved from the screen)
K4="$T/b084"; rm -rf "$K4"; mkdir -p "$K4/cfg" "$K4/bk"; sed -n '/^write_ks_conf()/,/^}/p' $ROOT/scripts/screen_board.sh > "$K4/f.sh"
printf '[printer WonderMaker]\nmoonraker_host: 10.9.9.9\nmoonraker_port: 7125\n\n[menu __main my_own]\nname: Mine\npanel: zr_tools\n\n[main]\nauto_open_extrude: False\n\n#~# --- Do not edit below this line. This section is auto generated --- #~#\n#~#\n#~# [main]\n#~# auto_open_extrude = False\n#~#\n' > "$K4/cfg/KlipperScreen.conf"
( DRY=0; CFG_DIR="$K4/cfg"; BK="$K4/bk"; PI_HOST=10.1.2.3; source "$K4/f.sh"; write_ks_conf; cp "$K4/cfg/KlipperScreen.conf" "$K4/one"; write_ks_conf )
check "B-084: a board install keeps an existing KlipperScreen.conf: own menu entry, [main], saved screen settings; new Pi address; missing ZR Tools entries added once; a backup is made; run twice = same" "grep -q '^moonraker_host: 10.1.2.3' $K4/cfg/KlipperScreen.conf && ! grep -q '10.9.9.9' $K4/cfg/KlipperScreen.conf && grep -q '^\[menu __main my_own\]' $K4/cfg/KlipperScreen.conf && grep -q '^auto_open_extrude: False' $K4/cfg/KlipperScreen.conf && grep -q '^#~# auto_open_extrude = False' $K4/cfg/KlipperScreen.conf && [ \$(grep -c '^\[menu __print zr_tools\]' $K4/cfg/KlipperScreen.conf) = 1 ] && [ \$(grep -c '^\[menu __splashscreen zr_tools\]' $K4/cfg/KlipperScreen.conf) = 1 ] && [ \$(grep -n '^\[menu __print zr_tools\]' $K4/cfg/KlipperScreen.conf | cut -d: -f1) -lt \$(grep -n '^#~# ' $K4/cfg/KlipperScreen.conf | head -1 | cut -d: -f1) ] && cmp -s $K4/one $K4/cfg/KlipperScreen.conf && ls $K4/cfg/backup/KlipperScreen.conf.wm-before-install-* >/dev/null"
K5="$T/b084n"; rm -rf "$K5"; mkdir -p "$K5/cfg" "$K5/bk"; ( DRY=0; CFG_DIR="$K5/cfg"; BK="$K5/bk"; PI_HOST=10.1.2.3; source "$K4/f.sh"; write_ks_conf )
check "B-084: a first board install writes the Pi address and the six ZR Tools menu entries (print menu included)" "grep -q '^moonraker_host: 10.1.2.3' $K5/cfg/KlipperScreen.conf && [ \$(grep -c '^\[menu ' $K5/cfg/KlipperScreen.conf) = 6 ] && grep -q '^\[menu __print zr_tools\]' $K5/cfg/KlipperScreen.conf && [ -f $K5/cfg/zr_screen.conf ]"
sec "== F-223: unload tip recipe by material"
check "F-223: the unload tip recipe is chosen by the material saved for the toolhead (PLA, PETG, ABS, default), never cooler than min_extrude_temp + 5" "python3 -I $ROOT/tests/test_tip_recipes.py"
sec "== NetworkManager option"
NM="$T/nm"; rm -rf "$NM"; mkdir -p "$NM"; mkstage "$T/stage_nm"; mkdir -p "$NM/.svc"; touch "$NM/.svc/dhcpcd.enabled"
inst "$NM" --from-stage "$T/stage_nm" --screen on >/dev/null
check "NetworkManager is never installed by the installer (F-234)" "! grep -q 'install -y network-manager' $NM/.sudo.log && grep -q 'WANT_NETMGR=0' $NM/wm-rpi-backup/install.conf"
mkdir -p "$NM/wm-rpi-backup"; echo dhcpcd-was-enabled > "$NM/wm-rpi-backup/netmgr.state"   # a Pi that an older installer switched: the switch back still works (erase uses it)
check "F-234: --network-manager, --screen-backend and --screen-remove are gone" "! bash $ROOT/installer.sh --network-manager on >/dev/null 2>&1 && ! bash $ROOT/installer.sh --screen-backend x11 >/dev/null 2>&1 && ! bash $ROOT/installer.sh --screen-remove >/dev/null 2>&1 && ! bash $ROOT/installer.sh --help | grep -q -e --network-manager -e --screen-remove -e --screen-backend"
check "F-234: the Add-ons and Uninstall menus no longer list the touchscreen or NetworkManager" "! M '3\n0\n0\n' $NM --menu | grep -q -e 'Touchscreen (KlipperScreen)' -e 'NetworkManager' && ! M '6\n0\n0\n' $NM --menu | grep -q -e 'Touchscreen (KlipperScreen)' -e 'NetworkManager'"
check "a saved dhcpcd state lets the user switch back" "[ -f $NM/wm-rpi-backup/netmgr.state ]"
check "--remove network-manager asks first" "M 'n\n' $NM --remove network-manager | grep -q 'Nothing changed' && [ -f $NM/wm-rpi-backup/netmgr.state ]"
: > "$NM/.sudo.log"
check "--remove network-manager switches back to dhcpcd at the next boot" "M 'y\n' $NM --remove network-manager | grep -q 'Reboot when you are ready' && grep -q 'systemctl enable dhcpcd' $NM/.sudo.log && grep -q 'systemctl disable NetworkManager' $NM/.sudo.log && [ ! -f $NM/wm-rpi-backup/netmgr.state ] && grep -q 'WANT_NETMGR=0' $NM/wm-rpi-backup/install.conf"
check "--remove network-manager does nothing when the installer did not switch it" "M 'y\n' $NM --remove network-manager | grep -q 'nothing to switch back'"
: > "$NM/.sudo.log"


sec "== Obico uses its own installer"
O2="$T/o2"; rm -rf "$O2"; mkdir -p "$O2"; mkstage "$T/stage_o2"; inst "$O2" --from-stage "$T/stage_o2" --screen off >/dev/null; printf "[server]\n" > "$O2/printer_data/config/moonraker.conf"; inst "$O2" --update --obico on >/dev/null
check "Obico is installed with its plain ./install.sh (no server flags, no server question)" "grep -q 'obico install.sh$' $O2/.sudo.log"
printf '[server]\nurl = http://x\n' > "$O2/printer_data/config/moonraker-obico.cfg"
check "--remove obico sets the settings file aside so a new install asks again" "M 'y\n' $O2 --remove obico | grep -q 'set aside' && [ ! -f $O2/printer_data/config/moonraker-obico.cfg ] && ls $O2/printer_data/config/moonraker-obico.cfg.wm-removed-*"

sec "== uninstall uses the add-on's own uninstaller"
UO="$T/uo"; mkun "$UO"; printf '\n[update_manager crowsnest]\ntype: git_repo\npath: ~/crowsnest\n\n[update_manager KlipperScreen]\ntype: git_repo\npath: ~/KlipperScreen\n\n[other]\nx: 1\n' >> "$UO/printer_data/config/moonraker.conf"
: > "$UO/.sudo.log"
M 'y\n' $UO --remove webcam >/dev/null
check "webcam: crowsnest's own 'make uninstall' runs first, before the installer's own cleanup" "grep -n 'official uninstall crowsnest: official_yes make uninstall' $UO/.sudo.log | head -1 | cut -d: -f1 | { read a; b=\$(grep -n 'systemctl stop crowsnest' $UO/.sudo.log | head -1 | cut -d: -f1); [ \$a -lt \$b ]; }"
check "webcam: its [update_manager crowsnest] section is removed, other sections stay, a copy is kept" "! grep -q 'update_manager crowsnest' $UO/printer_data/config/moonraker.conf && grep -q '^\[other\]' $UO/printer_data/config/moonraker.conf && ls $UO/printer_data/config/moonraker.conf.wm-before-crowsnest-removal-*"
mkdir -p "$UO/KlipperScreen"; inst2 "$UO" --update >/dev/null   # F-234: the update removes the KlipperScreen of the Pi by itself (no --remove screen any more)
check "touchscreen: KlipperScreen's own scripts/Uninstall.sh runs" "grep -q 'official uninstall KlipperScreen: bash scripts/Uninstall.sh' $UO/.sudo.log"
check "touchscreen: its [update_manager KlipperScreen] section is removed" "! grep -qi 'update_manager KlipperScreen' $UO/printer_data/config/moonraker.conf && grep -q '^\[other\]' $UO/printer_data/config/moonraker.conf"
OA="$T/oa"; rm -rf "$OA"; mkdir -p "$OA"; mkstage "$T/stage_oa"; inst "$OA" --from-stage "$T/stage_oa" --screen off >/dev/null; printf '[server]\nport: 7125\n' > "$OA/printer_data/config/moonraker.conf"
inst "$OA" --update --octoapp on --octoeverywhere on >/dev/null
M 'y\n' $OA --remove octoapp >/dev/null; M 'y\n' $OA --remove octoeverywhere >/dev/null
check "OctoApp and OctoEverywhere: their own ./uninstall.sh is the first step" "grep -q 'official uninstall octoapp: bash ./uninstall.sh' $OA/.sudo.log && grep -q 'official uninstall octoeverywhere: bash ./uninstall.sh' $OA/.sudo.log"
check "Obico: the steps from its own uninstall list are done (service, reset-failed, include lines)" "sed -n '/^do_remove_addon_core()/,/^}/p' $ROOT/installer.sh | grep -q 'reset-failed' && sed -n '/^do_remove_addon_core()/,/^}/p' $ROOT/installer.sh | grep -q 'include moonraker-obico-update.cfg' && sed -n '/^do_remove_addon_core()/,/^}/p' $ROOT/installer.sh | grep -q 'include moonraker_obico_macros.cfg'"


sec "== leftovers and administrator rights"
check "files that cannot be deleted as the user are deleted with sudo" "sed -n '/^rm_path()/,/^}/p' $ROOT/installer.sh | grep -q 'SUDO rm -rf'"
CS="$T/cs"; mkun "$CS"; mkdir -p "$CS/wm-stage"; echo x > "$CS/wm-stage/k.tgz"
check "clean-up lists the copy from the old board and needs DELETE for it" "M '4\nno\n0\n' $CS --remove cleanup | grep -q 'Nothing changed' && [ -d $CS/wm-stage ] && M '4\nDELETE\n0\n' $CS --remove cleanup | grep -q 'Deleted: Software copied from the old board' && [ ! -e $CS/wm-stage ]"
check "OctoApp removal also deletes its installer log and config files" "mkdir -p $OA/printer_data/config && touch $OA/octoeverywhere-installer.log $OA/printer_data/config/octoeverywhere.conf $OA/printer_data/config/octoeverywhere-system.cfg && mkdir -p $OA/octoeverywhere $OA/octoeverywhere-env && M 'y\n' $OA --remove octoeverywhere >/dev/null && [ ! -e $OA/octoeverywhere-installer.log ] && [ ! -e $OA/printer_data/config/octoeverywhere.conf ] && [ ! -e $OA/printer_data/config/octoeverywhere-system.cfg ] && [ ! -e $OA/octoeverywhere-env ]"


sec "== log of every run"
LG="$T/lg"; rm -rf "$LG"; mkdir -p "$LG"; mkstage "$T/stage_lg"
WM_FORCE_LOG=1 inst "$LG" --from-stage "$T/stage_lg" --screen off >/dev/null; sleep 1
LF="$(ls -1t $LG/wm-install-logs/installer-install-*.log 2>/dev/null | head -1)"
check "an install writes a log in ~/wm-install-logs" "[ -n \"$LF\" ] && grep -q 'Plan (nothing has been changed yet)' \"$LF\" && grep -q 'Self-test' \"$LF\""
check "the log has no colour codes and no leftover .raw file" "! grep -q \$'\\x1b' \"$LF\" && ! ls $LG/wm-install-logs/*.raw"
check "the log is private (600) and so is its folder" "[ \"\$(stat -c %a \"$LF\")\" = 600 ] && [ \"\$(stat -c %a $LG/wm-install-logs)\" = 700 ]"
check "--show-log says where the log is and shows its end" "M '' $LG --show-log | grep -q 'Newest log: .*installer-install-' "
check "the support bundle contains the newest run log" "M '' $LG --support-bundle >/dev/null; tar tzf \$(ls -1t $LG/wm-support-*.tgz | head -1) | grep -q 'logs/last-installer-run.log'"
rm -rf "$LG/wm-install-logs"; M '' $LG --check >/dev/null; M '0\n' $LG --menu >/dev/null; M '' $LG --check-updates >/dev/null 2>&1; inst "$LG" --dry-run --update >/dev/null 2>&1
check "read-only runs, the menu and --dry-run write no log" "[ ! -d $LG/wm-install-logs ] || [ -z \"\$(ls $LG/wm-install-logs)\" ]"
check "without WM_FORCE_LOG the test runs write no log" "inst $LG --update >/dev/null; [ ! -d $LG/wm-install-logs ] || [ -z \"\$(ls $LG/wm-install-logs)\" ]"
python3 - "$ROOT" "$LG" <<'PY'
import pty, os, sys, time, select
root, home = sys.argv[1], sys.argv[2]
env = dict(os.environ, WM_HOME=home, WM_INSTALLER_TEST="1", WM_FORCE_LOG="1")
pid, fd = pty.fork()
if pid == 0:
    os.execvpe("bash", ["bash", root + "/installer.sh", "--backup"], env)
out = b""; t = time.time()
while time.time() - t < 15:
    r, _, _ = select.select([fd], [], [], 0.5)
    if r:
        try: d = os.read(fd, 4096)
        except OSError: break
        if not d: break
        out += d
os.waitpid(pid, 0)
open(home + "/pty.out", "wb").write(out)
PY
check "at a terminal the run is recorded through script, shown normally, and the log path is printed" "grep -q 'Log of this run' $LG/pty.out && ls $LG/wm-install-logs/installer-backup-*.log && grep -q 'Backup of your printer settings' \$(ls $LG/wm-install-logs/installer-backup-*.log | head -1) && ! grep -q \$'\\x1b' \$(ls $LG/wm-install-logs/installer-backup-*.log | head -1)"
check "clean-up lists the logs with a y/n" "mkdir -p $LG/wm-install-logs && echo x > $LG/wm-install-logs/installer-x.log && M '3\nn\n0\n' $LG --remove cleanup | grep -q 'Installer logs' && M '3\ny\n0\n' $LG --remove cleanup | grep -q 'Deleted: Installer logs' && [ ! -e $LG/wm-install-logs ]"

sec "== settings import from the old board"
IM="$T/imp"; mkdir -p "$IM/old" "$IM/home/printer_data/config"
cat > "$IM/old/printer.cfg" <<'CFG'
[mcu]
canbus_uuid: OLD
[extruder]
pid_Kp: 1.0

#*# <---------------------- SAVE_CONFIG ---------------------->
#*# DO NOT EDIT THIS BLOCK OR BELOW. The contents are auto-generated.
#*#
#*# [extruder]
#*# control = pid
#*# pid_kp = 31.5
#*#
#*# [probe]
#*# z_offset = -0.130
#*#
#*# [mcu rpi]
#*# serial = nope
CFG
printf '[Variables]\nt0_offset = (0.1, 0.2, 0.3)\ncurrent_extruder = 3\n' > "$IM/old/saved_variables.cfg"
printf '[mcu]\ncanbus_uuid: NEW\n[extruder]\npid_Kp: 22.0\ncontrol: pid\n' > "$IM/home/printer_data/config/printer.cfg"
printf '[Variables]\nt0_offset = (0.0, 0.0, 0.0)\ncurrent_extruder = 0\n' > "$IM/home/printer_data/config/saved_variables.cfg"
check "import: --dry-run changes nothing" "WM_HOME=$IM/home WM_INSTALLER_TEST=1 WM_IMPORT_FROM_DIR=$IM/old bash $ROOT/installer.sh --import-settings 192.0.2.9 --dry-run | grep -q 'dry run' && ! grep -q SAVE_CONFIG $IM/home/printer_data/config/printer.cfg"
check "import: applies the SAVE_CONFIG block, comments the override, keeps canbus_uuid, no mcu section" "echo y | WM_HOME=$IM/home WM_INSTALLER_TEST=1 WM_IMPORT_FROM_DIR=$IM/old bash $ROOT/installer.sh --import-settings 192.0.2.9 >/dev/null 2>&1; f=$IM/home/printer_data/config/printer.cfg; grep -q 'pid_kp = 31.5' \$f && grep -q 'z_offset = -0.130' \$f && grep -q '^#pid_Kp: 22.0' \$f && grep -q 'canbus_uuid: NEW' \$f && ! grep -q 'mcu rpi' \$f && ls \$f.wm-before-import-* >/dev/null"
check "import: only calibration variables are copied" "grep -q 't0_offset = (0.1, 0.2, 0.3)' $IM/home/printer_data/config/saved_variables.cfg && grep -q 'current_extruder = 0' $IM/home/printer_data/config/saved_variables.cfg"
check "import: --from-board is refused" "! bash $ROOT/installer.sh --from-board 1.2.3.4 >/dev/null 2>&1"

sec "== check-updates and zr_tools.cfg backup"
mkdir -p "$T/cu"; ( cd "$T/cu" && git init -q --bare origin.git && git clone -q origin.git work 2>/dev/null && cd work && git config user.email t@t && git config user.name t && echo 1.0.0 > VERSION && git add -A && git commit -q -m first && git push -q origin HEAD:main 2>/dev/null; git branch -q -M main; git push -q -u origin main 2>/dev/null; cd .. && git clone -q origin.git copy && cd copy && git checkout -q main 2>/dev/null; cd ../work && echo 1.1.0 > VERSION && git commit -q -am "new thing" && git push -q origin main )
cp "$ROOT/installer.sh" "$T/cu/copy/installer.sh"
mkdir -p "$T/cu/copy/scripts"; cp "$ROOT/scripts/lib_free_space.sh" "$T/cu/copy/scripts/"
check "--check-updates lists new changes" "bash $T/cu/copy/installer.sh --check-updates | grep -q 'new thing'"
check "--check-updates shows the new version" "bash $T/cu/copy/installer.sh --check-updates | grep -q '1.1.0'"
( cd "$T/cu/copy" && git pull -q origin main 2>/dev/null; git checkout -q -- installer.sh 2>/dev/null; true )
check "--check-updates says latest when level" "cp $ROOT/installer.sh $T/cu/copy/installer.sh; mkdir -p $(dirname $T/cu/copy/installer.sh)/scripts; cp $ROOT/scripts/lib_free_space.sh $(dirname $T/cu/copy/installer.sh)/scripts/; bash $T/cu/copy/installer.sh --check-updates | grep -q 'latest version'"
check "--check-updates outside a git clone compares version numbers" "mkdir -p $T/nogit && cp $ROOT/installer.sh $ROOT/VERSION $T/nogit/; mkdir -p $T/nogit/scripts; cp $ROOT/scripts/lib_free_space.sh $T/nogit/scripts/ && WM_TEST_NEW_VERSION=99.0.0 bash $T/nogit/installer.sh --check-updates | grep -q \"On GitHub: *installer 99.0.0\""
ZH="$T/zrhome"; mkdir -p "$ZH/printer_data/config"; echo "[mcu]" > "$ZH/printer_data/config/printer.cfg"
HOME="$ZH" ZR_NO_RESTART=1 bash "$ROOT/zr_tools/install_zr_tools.sh" >/dev/null 2>&1
echo "# my edit" >> "$ZH/printer_data/config/zr_tools.cfg"
HOME="$ZH" ZR_NO_RESTART=1 bash "$ROOT/zr_tools/install_zr_tools.sh" >/dev/null 2>&1
check "an edited zr_tools.cfg is kept as a backup before being replaced" "grep -q 'my edit' $ZH/printer_data/config/zr_tools.cfg.zrbak_* && ! grep -q 'my edit' $ZH/printer_data/config/zr_tools.cfg"
HOME="$ZH" ZR_NO_RESTART=1 bash "$ROOT/zr_tools/install_zr_tools.sh" >/dev/null 2>&1
check "no extra backup when zr_tools.cfg is unchanged" "[ \$(ls $ZH/printer_data/config/zr_tools.cfg.zrbak_* | wc -l) = 1 ]"
check "bad --screen-layout value fails" "! bash $ROOT/installer.sh --screen-layout round"
check "screen python tests" "python3 -I -W ignore $ROOT/tests/test_screen.py"
check "chamber light python tests" "python3 -I -W ignore $ROOT/tests/test_chamber_light.py"
check "KlipperScreen updating page patch" "python3 -I -W ignore $ROOT/tests/test_ks_update.py"
check "python files compile" "for f in $ROOT/zr_tools/*.py; do python3 -I -m py_compile \$f || exit 1; done"

sec "== dry run changes nothing"
H4="$T/h4"; mkdir -p "$H4"
inst "$H4" --dry-run --from-stage "$T/stage" > "$T/dry.out"
check "dry run: nothing unpacked" "[ ! -d $H4/klipper ]"
check "dry run: says would run" "grep -q 'would run' $T/dry.out"
check "dry run: no sudo log" "[ ! -s $H4/.sudo.log ]"
WM_HOME="$H4" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --dry-run --from-stage "$T/stage" > "$T/dry-nopanel.out" 2>&1
check "dry run without a panel download: the panel step says it would download the panel and does not report a failed download or a missing web page" "grep -q 'would download the newest Fluidd panel' $T/dry-nopanel.out && ! grep -q 'panel could not be downloaded' $T/dry-nopanel.out && ! grep -q 'Fluidd web page was NOT installed' $T/dry-nopanel.out"

check "install: wm_sv_guard.sh copied and executable" "[ -x $H/printer_data/scripts/wm_sv_guard.sh ]"
check "install: guard timer enabled and started" "grep -q 'systemctl enable wm-sv-guard.timer' $H/.sudo.log && grep -q 'systemctl start wm-sv-guard.timer' $H/.sudo.log"
check "install: guard service files installed" "grep -q 'wm-sv-guard.service' $H/.sudo.log && grep -q 'wm-sv-guard.timer' $H/.sudo.log"
sec "== check / enable / disable / uninstall"
check "--check passes on installed home" "WM_HOME=$H WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --check"
mkdir -p "$T/empty"; check "--check fails on empty home" "! WM_HOME=$T/empty WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --check"
inst "$H" --disable-klipper >/dev/null; check "--disable-klipper" "grep -q 'systemctl disable klipper' $H/.sudo.log"
: > "$H/.sudo.log"; printf 'n\n' | WM_HOME="$H" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --enable-klipper >/dev/null 2>&1
check "--enable-klipper asks first (default no)" "! grep -q 'systemctl enable klipper' $H/.sudo.log"
printf 'y\n' | WM_HOME="$H" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --uninstall >/dev/null 2>&1
check "uninstall removes service file" "grep -q 'rm -f /etc/systemd/system/klipper.service' $H/.sudo.log"
check "uninstall stops and removes the saved_variables safeguard timer" "grep -q 'rm -f /etc/systemd/system/wm-sv-guard.timer' $H/.sudo.log"
check "uninstall keeps user folders" "[ -d $H/klipper/klippy ] && [ -f $H/printer_data/config/printer.cfg ]"

sec "== missing / broken stage"
mkdir -p "$T/bad"; check "incomplete stage refused" "! inst $T/h5 --from-stage $T/bad"
check "wrong user refused outside test mode" "! WM_HOME=$T/h6 bash $ROOT/installer.sh --from-stage $T/stage </dev/null"

sec "== factory files from the repository (no printer)"
(cd "$ROOT/factory/ultra-s" && sha256sum -c SHA256SUMS >/dev/null) && echo "  ok   factory checksums" && PASS=$((PASS+1))
check "factory sources are plain folders, committed" "[ -f $ROOT/factory/ultra-s/klipper/klippy/klippy.py ] && [ -f $ROOT/factory/ultra-s/moonraker/moonraker/moonraker.py ] && ! git -C $ROOT check-ignore -q factory/ultra-s/klipper/klippy/klippy.py"
check "ZR_PURGE is gone from zr_tools.cfg and the touchscreen (F-104), ZR_LOAD, ZR_RETRACT and ZR_UNLOAD use the shared tip step" "! grep -q 'ZR_PURGE\|_act_purge' $ROOT/zr_tools/zr_tools.cfg $ROOT/zr_tools/INSTALL.md && ! grep -q '_act_purge\|\"ZR_PURGE\"' $ROOT/zr_tools/zr_tools.py && grep -q 'gcode_macro _WM_UNLOAD_TIP' $ROOT/zr_tools/zr_tools.cfg && grep -q 'gcode_macro _ZR_LOAD' $ROOT/zr_tools/zr_tools.cfg"
for m in ultra ultra-s; do
  check "$m: M191 strips the = from BED_TEMP (Klipper passes it as =65)" "grep -q 'params.BED_TEMP|default(bed_assist_temp)|string|replace(\"=\", \"\")' $ROOT/factory/$m/config/macros.cfg"
done
for m in ultra ultra-s; do
  check "$m: M191 has the chamber limit, the fans, the nozzle preheat and the bed assist" "awk '/gcode_macro M191/{f=1} /gcode_macro _RGB_CLOSE/{f=0} f' $ROOT/factory/$m/config/macros.cfg | grep -q 'variable_max_chamber' && awk '/gcode_macro M191/{f=1} /gcode_macro _RGB_CLOSE/{f=0} f' $ROOT/factory/$m/config/macros.cfg | grep -q 'params.BED_TEMP' && awk '/gcode_macro M191/{f=1} /gcode_macro _RGB_CLOSE/{f=0} f' $ROOT/factory/$m/config/macros.cfg | grep -q 'auxiliary_fan' && grep -q 'variable_bed_assist_temp' $ROOT/factory/$m/config/macros.cfg"
done
for m in ultra ultra-s; do
  check "$m: z_rise is the fixed one (reads stepper_z, no last_query.z test) in rpi_base.cfg, and printer.cfg and the 4 variants no longer have it" "grep -q 'gcode_macro _z_rise_run' $ROOT/rpi-cfg/rpi_base.cfg && grep -q 'q.stepper_z' $ROOT/rpi-cfg/rpi_base.cfg && ! grep -q 'last_query.z==0' $ROOT/rpi-cfg/rpi_base.cfg && (for f in $ROOT/factory/$m/config/printer.cfg $ROOT/factory/$m/config-variants/printer?.cfg; do ! grep -qE '^\\[(gcode_macro _z_rise_run|gcode_macro z_rise|homing_override|gcode_macro _Z_HOMING|idle_timeout)\\]' \$f || exit 1; done)"
  check "$m: z_rise runs first in _UNLOCK_TOOL, _LOCK_TOOL, WIPE_NOZZLE, EXTRUDE_FILAMENT, RETRACT_FILAMENT, filament_insert_gcode" "[ \$(grep -c '^    z_rise\$' $ROOT/factory/$m/config/change_macros.cfg) = 2 ] && [ \$(grep -c '^    z_rise\$' $ROOT/factory/$m/config/fz-wipe-nozzle.cfg) = 1 ] && ! grep -q WIPE_NOZZLE_SIMPLE $ROOT/factory/$m/config/fz-wipe-nozzle.cfg && [ \$(grep -c '^    z_rise\$' $ROOT/factory/$m/config/macros.cfg) = 3 ]"
done
check "the 5 compiled modules are in the repo and match their factory checksums" "cd $ROOT/factory/ultra-s/klipper && sha256sum -c ../modules.sha256"
check "klipper archive has its license" "[ -f $ROOT/factory/ultra-s/klipper/COPYING ] && [ -f $ROOT/factory/ultra-s/moonraker/LICENSE ]"
check "factory config has placeholder CAN ids (main board, hub, extruder board) and empty ones for T0-T3 and the load cell, which the installer fills" "grep -q 'canbus_uuid: 000000000000' $ROOT/factory/ultra-s/config/wm_zru_mcu.cfg && [ \$(cat $ROOT/factory/ultra-s/config/wm_zru_*.cfg | grep -ic \"canbus_uuid: [0-9a-f]\\{12\\}\") = 3 ]"
HG="$T/hg"; mkdir -p "$HG"
OUT="$(inst "$HG" --from-github --model ultra-s)"; echo "$OUT" > "$T/gh.out"
check "install from repo works" "[ -f $HG/klipper/klippy/klippy.py ] && [ -f $HG/printer_data/config/printer.cfg ]"
check "no missing-modules warning (they are bundled)" "! grep -q 'compiled modules were NOT installed' $T/gh.out && grep -q 'all 5 present' $T/gh.out"
check "bundled modules end up in ~/klipper" "ls $HG/klipper/klippy/extras/hx711.cpython-39-aarch64-linux-gnu.so"
check "web interface installed (factory data has none)" "[ -f $HG/fluidd/index.html ]"
check "env files in place" "grep -q KLIPPER_ARGS $HG/printer_data/systemd/klipper.env"
check "unknown model refused" "! inst $T/hg2 --from-github --model nope"
check "ultra-s model enables zru-s.cfg" "grep -q '^\\[include zru-s.cfg\\]' $HG/printer_data/config/printer.cfg"
HU="$T/hu"; mkdir -p "$HU"; inst "$HU" --from-github --model ultra >/dev/null
check "ultra has its own factory folder" "[ -d $ROOT/factory/ultra/klipper/klippy ] && [ -f $ROOT/factory/ultra/config/printer.cfg ]"
check "ultra folder: zru-s.cfg off, ultra-s folder: on" "grep -q '^# \\[include zru-s.cfg\\]' $ROOT/factory/ultra/config/printer.cfg && grep -q '^\\[include zru-s.cfg\\]' $ROOT/factory/ultra-s/config/printer.cfg"
check "both folders pass their checksums" "(cd $ROOT/factory/ultra && sha256sum -c SHA256SUMS) && (cd $ROOT/factory/ultra-s && sha256sum -c SHA256SUMS)"
check "ultra model leaves zru-s.cfg off" "grep -q '^# \\[include zru-s.cfg\\]' $HU/printer_data/config/printer.cfg && ! grep -q '^\\[include zru-s.cfg\\]' $HU/printer_data/config/printer.cfg"
check "rpi-cfg: rpi_calibration.cfg is installed and included, ultra-s and ultra" "cmp $ROOT/rpi-cfg/rpi_calibration.cfg $HG/printer_data/config/rpi_calibration.cfg && grep -q '^\\[include rpi_calibration.cfg\\]' $HG/printer_data/config/printer.cfg && cmp $ROOT/rpi-cfg/rpi_calibration.cfg $HU/printer_data/config/rpi_calibration.cfg && grep -q '^\\[include rpi_calibration.cfg\\]' $HU/printer_data/config/printer.cfg"
check "rpi-cfg: rpi_base.cfg (switch pins, safety, print end, tool LEDs, head sensors, unload menu, SET_GCODE_OFFSET) is installed and included, ultra-s and ultra" "cmp $ROOT/rpi-cfg/rpi_base.cfg $HG/printer_data/config/rpi_base.cfg && grep -q '^\\[include rpi_base.cfg\\]' $HG/printer_data/config/printer.cfg && cmp $ROOT/rpi-cfg/rpi_base.cfg $HU/printer_data/config/rpi_base.cfg && grep -q '^\\[include rpi_base.cfg\\]' $HU/printer_data/config/printer.cfg && grep -q '^\\[delayed_gcode WM_TOOL_LEDS\\]' $ROOT/rpi-cfg/rpi_base.cfg && grep -q '^\\[delayed_gcode WM_PRINT_END_WATCH\\]' $ROOT/rpi-cfg/rpi_base.cfg && grep -q '^\\[gcode_macro SET_GCODE_OFFSET\\]' $ROOT/rpi-cfg/rpi_base.cfg"
MT="$T/mt"; rm -rf "$MT"; mkdir -p "$MT"; cp "$ROOT/tests/fixtures/moonraker_wm_style.conf" "$MT/old.conf"
sed -i 's|^frame_path:.*|frame_path: /tmp/timelapse/|; /^camera:/d' "$MT/old.conf"
check "moonraker: conf fix adds the K1 sections, frames folder and timelapse options, and is idempotent" "python3 -I $ROOT/scripts/wm_moonraker_conf.py conf $MT/old.conf --write >/dev/null; [ \$? = 10 ]; grep -q '^frame_path: ~/printer_data/frames/' $MT/old.conf && grep -q '^camera: default' $MT/old.conf && grep -q '^parkpos: back_right' $MT/old.conf && grep -q '^\\[file_manager\\]' $MT/old.conf && grep -q '^\\[machine\\]' $MT/old.conf && python3 -I $ROOT/scripts/wm_moonraker_conf.py conf $MT/old.conf >/dev/null"
check "moonraker: the console keeps 1000 lines (data_store), your own value is kept" "grep -q '^\\[data_store\\]' $MT/old.conf && grep -q '^gcode_store_size: 1000' $MT/old.conf; printf '[data_store]\ngcode_store_size: 2000\n' > $MT/ds.conf; python3 -I $ROOT/scripts/wm_moonraker_conf.py conf $MT/ds.conf --write >/dev/null; grep -q '^gcode_store_size: 2000' $MT/ds.conf"
check "moonraker: your own timelapse values are not changed" "printf '[timelapse]\nframe_path: /mnt/x/\nparkpos: front_left\n' > $MT/own.conf; python3 -I $ROOT/scripts/wm_moonraker_conf.py conf $MT/own.conf --write >/dev/null; grep -q '^frame_path: /mnt/x/' $MT/own.conf && grep -q '^parkpos: front_left' $MT/own.conf && [ \$(grep -c '^parkpos' $MT/own.conf) = 1 ]"
check "moonraker: factory moonraker.conf (both models) is already complete" "( for m in ultra ultra-s; do python3 -I $ROOT/scripts/wm_moonraker_conf.py conf $ROOT/factory/\$m/config/moonraker.conf >/dev/null || exit 1; done )"
check "moonraker: the timelapse step adds [update_manager timelapse] and the frames folder" "[ -d $HG/printer_data/frames ] && grep -q '^\\[update_manager timelapse\\]' $HG/printer_data/config/moonraker.conf"
check "moonraker: the timelapse step also adds the [timelapse] section so the component loads" "grep -q '^\\[timelapse\\]' $HG/printer_data/config/moonraker.conf && grep -q '^frame_path: ~/printer_data/frames/' $HG/printer_data/config/moonraker.conf"
check "rpi-cfg: rpi_base.cfg (homing, z_rise, idle timeout, bed warp wait) is installed and included, ultra-s and ultra, and no separate rpi_homing.cfg" "cmp $ROOT/rpi-cfg/rpi_base.cfg $HG/printer_data/config/rpi_base.cfg && grep -q '^\\[include rpi_base.cfg\\]' $HG/printer_data/config/printer.cfg && cmp $ROOT/rpi-cfg/rpi_base.cfg $HU/printer_data/config/rpi_base.cfg && grep -q '^\\[include rpi_base.cfg\\]' $HU/printer_data/config/printer.cfg && ! grep -q '^\\[homing_override\\]' $HG/printer_data/config/printer.cfg && [ ! -e $HG/printer_data/config/rpi_homing.cfg ]"
check "rpi-cfg: calibration windows close on the screen too (prompt_end in the start, stop, save and cancel paths)" "W=$ROOT/rpi-cfg/rpi_calibration.cfg; sed -n '/^\\[gcode_macro _WM_CAL_PRECHECK\\]/,/^\\[gcode_macro _WM_CAL_ASK\\]/p' \$W | grep -q prompt_end && sed -n '/^\\[gcode_macro _WM_CAL_STOP\\]/,/^\\[gcode_macro _WM_PROMPT_CLOSE\\]/p' \$W | grep -q prompt_end && grep -q 'Save and Restart|_WM_SAVE|' \$W && grep -q 'Cancel|_WM_PROMPT_CLOSE' \$W && ! grep -q 'Cancel|M118' \$W"
check "rpi-cfg: bed leveling, vibration compensation and bed PID say which step they are on" "W=$ROOT/rpi-cfg/rpi_calibration.cfg; for m in 'Bed leveling - step 2' 'Vibration compensation - step 2' 'Bed PID - heating'; do grep -q \"\$m\" \$W || exit 1; done"
check "rpi-cfg: exactly one include line, and printer.cfg was saved first" "[ \$(grep -c 'include rpi_calibration.cfg' $HG/printer_data/config/printer.cfg) = 1 ] && [ -n \"\$(ls $HG/printer_data/config/printer.cfg.wm-before-rpicfg-* $HG/printer_data/config/backup/printer.cfg.wm-before-rpicfg-* $HG/ultra-backup/config/*/printer.cfg.wm-before-rpicfg-* 2>/dev/null)\" ]"
check "rpi-cfg: the include sits before the SAVE_CONFIG block, not after it" "! sed -n '/SAVE_CONFIG/,\$p' $HG/printer_data/config/printer.cfg | grep -q 'include rpi_calibration'"
check "rpi-cfg: the macros render and behave (jinja2)" "python3 $ROOT/tests/rpi_cfg_render.py; r=\$?; [ \$r = 0 ] || [ \$r = 77 ]"
check "rpi-cfg: every WonderMaker macro it calls exists in both factory folders" "for m in G29 PROBE_CALIBRATE CALIBRATE_OFFSET_ALL_RAPID_MODE NOZZLE_PREPARE NOZZLE_CALIBRATE_TOOL_OFFSET RAPID_MODE PARK_CURRENT_TOOL; do for d in ultra ultra-s; do grep -q \"^\\[gcode_macro \$m\\]\" $ROOT/factory/\$d/config/*.cfg || exit 1; done; done"
check "MCU firmware and flasher match their checksums" "cd $ROOT/factory/ultra-s/mcu && sha256sum -c binaries.sha256"
check "model variants of printer.cfg present" "[ -f $ROOT/factory/ultra-s/config-variants/printer4.cfg ]"
# modules: wrong files refused, right files accepted (use a copy of the repo with matching fake checksums)
mkdir -p "$T/mods"; for n in cs1237 heater_air_core heater_feng hx711 xy_offset_calibrator_core; do echo "fake $n" > "$T/mods/$n.cpython-39-aarch64-linux-gnu.so"; done
check "modules with wrong checksum refused" "! bash $ROOT/scripts/stage_from_repo.sh ultra-s $T/st_bad $T/mods"
RC2="$T/repocopy"; mkdir -p "$RC2"; cp -a "$ROOT/scripts" "$ROOT/config" "$ROOT/factory" "$RC2/"
( cd "$T/mods" && sha256sum *.so | sed 's#  #  klippy/extras/#' ) > "$RC2/factory/ultra-s/modules.sha256"
check "modules with matching checksum accepted" "bash $RC2/scripts/stage_from_repo.sh ultra-s $T/st_ok $T/mods && [ \"\$(cat $T/st_ok/modules_ok)\" = 1 ] && tar xzOf $T/st_ok/klipper.tgz klipper/klippy/extras/hx711.cpython-39-aarch64-linux-gnu.so | grep -q 'fake hx711'"
check "damaged repo files refused" "cp -a $ROOT/factory $T/damaged_f && echo x >> $T/damaged_f/ultra-s/moonraker/README.md && mkdir -p $T/dm && cp -a $ROOT/scripts $ROOT/config $T/dm/ && rm -rf $T/dm/factory && cp -a $T/damaged_f $T/dm/factory && ! bash $T/dm/scripts/stage_from_repo.sh ultra-s $T/st_dm"

sec "== crowsnest, timelapse, pinned environments"
check "addon pins are full commit ids" "grep -qE '^crowsnest\\|https://github.com/mainsail-crew/crowsnest\\|[0-9a-f]{40}\$' $ROOT/config/pins/addons.txt && grep -qE '^moonraker-timelapse\\|.*\\|[0-9a-f]{40}\$' $ROOT/config/pins/addons.txt"
check "klippy requirements all pinned" "! grep -vE '^#|==' $ROOT/config/klippy-requirements.txt | grep -q ."
check "moonraker requirements all pinned" "! grep -vE '^#|==' $ROOT/config/moonraker-requirements.txt | grep -q ."
check "timelapse.cfg shipped (printer.cfg includes it)" "[ -f $ROOT/factory/ultra-s/config/timelapse.cfg ] && grep -q 'include timelapse.cfg' $ROOT/factory/ultra-s/config/printer.cfg"
check "every include of the factory printer.cfg exists" "cd $ROOT/factory/ultra-s/config && for f in \$(grep -E '^\\[include ' printer.cfg | sed 's/\\[include //;s/\\]//'); do [ -f \$f ] || { echo missing \$f; exit 1; }; done"
check "crowsnest installed (unattended) in test log" "grep -q 'make install (crowsnest)' $HG/.sudo.log"
check "crowsnest.conf placed" "[ -f $HG/printer_data/config/crowsnest.conf ]"
check "ffmpeg requested for timelapse" "grep -q 'apt-get install -y ffmpeg' $HG/.sudo.log"
check "moonraker.asvc lists crowsnest" "grep -q crowsnest $HG/printer_data/moonraker.asvc"
sec "== Fluidd update: the Update button applies the installer"
check "update manager: the installer entry says the Update button applies the update" "grep -A8 '^\[update_manager wm_ultra_vanilla_klipper\]' $HG/printer_data/config/moonraker.conf | grep -q 'The Update button downloads the new installer and applies it'"
check "update button: the watcher units are installed and enabled" "grep -q 'install -m 644 .*/etc/systemd/system/wm-pi-update.path' $HG/.sudo.log && grep -q 'install -m 644 .*/etc/systemd/system/wm-pi-update.service' $HG/.sudo.log && grep -q 'systemctl enable --now wm-pi-update.path' $HG/.sudo.log"
check "update button: the path unit watches this folder's git log, the service runs pi_update.sh as the user" "grep -q '^PathModified=.*/.git/logs/HEAD' $HG/.wm-units/wm-pi-update.path && grep -q '^ExecStart=/bin/bash .*/scripts/pi_update.sh' $HG/.wm-units/wm-pi-update.service && grep -q '^User=' $HG/.wm-units/wm-pi-update.service && grep -q '^Type=oneshot' $HG/.wm-units/wm-pi-update.service"
check "update button: both units are recorded for the uninstall" "grep -q 'wm-pi-update.path' $HG/wm-rpi-backup/installed.manifest && grep -q 'wm-pi-update.service' $HG/wm-rpi-backup/installed.manifest"
check "update manager: a second run does not duplicate the entry" "inst $HG --update --only-addon webcam --webcam on >/dev/null; [ \$(grep -c '^\[update_manager wm_ultra_vanilla_klipper\]' $HG/printer_data/config/moonraker.conf) = 1 ]"
sec "== F-242 installer folder without capital letters"
MG="$T/mg"; rm -rf "$MG"; mkdir -p "$MG"; cp -a "$HG" "$MG/home" 2>/dev/null; MH="$MG/home"; rm -rf "$MH/WM_Ultra_Vanilla_Klipper" "$MH/wm_ultra_vanilla_klipper"; cp -al "$ROOT" "$MH/WM_Ultra_Vanilla_Klipper"
printf '\n[update_manager WM_Ultra_Vanilla_Klipper]\ntype: git_repo\npath: %s/WM_Ultra_Vanilla_Klipper\norigin: https://github.com/ducati1198/WM_Ultra_Vanilla_Klipper.git\nprimary_branch: main\nis_system_service: False\n' "$MH" > "$MG/old_entry.txt"
python3 - "$MH/printer_data/config/moonraker.conf" "$MG/old_entry.txt" <<'PY'
import sys, re
p, e = sys.argv[1], sys.argv[2]; out = []; skip = False
for l in open(p).read().split("\n"):
    m = re.match(r"\s*\[(.+?)\]", l)
    if m: skip = m.group(1).strip().lower() == "update_manager wm_ultra_vanilla_klipper"
    if not skip: out.append(l)
open(p, "w").write("\n".join(out) + open(e).read())
PY
check "F-242 setup: the test home has the old capital entry and the old folder" "grep -q '^\[update_manager WM_Ultra_Vanilla_Klipper\]' $MH/printer_data/config/moonraker.conf && [ -d $MH/WM_Ultra_Vanilla_Klipper/.git ]"
WM_TEST_PANEL_DIR="$T/stubpanel" WM_HOME="$MH" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$MH/WM_Ultra_Vanilla_Klipper/installer.sh" --update --only-addon webcam --webcam on > "$MG/run1.log" 2>&1
check "F-242 an update run moves ~/WM_Ultra_Vanilla_Klipper to ~/wm_ultra_vanilla_klipper" "[ -d $MH/wm_ultra_vanilla_klipper/.git ] && [ -f $MH/wm_ultra_vanilla_klipper/installer.sh ]"
check "F-242 no capital-letter name is left behind (no folder, no link)" "[ ! -e $MH/WM_Ultra_Vanilla_Klipper ] && [ ! -L $MH/WM_Ultra_Vanilla_Klipper ]"
check "F-242 Fluidd has one entry with the new name and the new folder, the old entry is gone" "[ \$(grep -ci '^\[update_manager wm_ultra_vanilla_klipper\]' $MH/printer_data/config/moonraker.conf) = 1 ] && grep -q '^\[update_manager wm_ultra_vanilla_klipper\]' $MH/printer_data/config/moonraker.conf && ! grep -q '^\[update_manager WM_Ultra_Vanilla_Klipper\]' $MH/printer_data/config/moonraker.conf && grep -A3 '^\[update_manager wm_ultra_vanilla_klipper\]' $MH/printer_data/config/moonraker.conf | grep -q \"^path: $MH/wm_ultra_vanilla_klipper\$\""
check "F-242 the update service units point at the new folder" "grep -q \"^PathModified=$MH/wm_ultra_vanilla_klipper/.git/logs/HEAD\" $MH/.wm-units/wm-pi-update.path && grep -q \"^ExecStart=/bin/bash $MH/wm_ultra_vanilla_klipper/scripts/pi_update.sh\" $MH/.wm-units/wm-pi-update.service"
check "F-242 a copy of the old moonraker.conf is kept" "ls $MH/printer_data/config/moonraker.conf.wm-before-* >/dev/null 2>&1"
WM_TEST_PANEL_DIR="$T/stubpanel" WM_HOME="$MH" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$MH/wm_ultra_vanilla_klipper/installer.sh" --update --only-addon webcam --webcam on > "$MG/run2.log" 2>&1
check "F-242 a second run changes nothing (one entry, no capital-letter name, no warning)" "[ \$(grep -ci '^\[update_manager wm_ultra_vanilla_klipper\]' $MH/printer_data/config/moonraker.conf) = 1 ] && [ ! -e $MH/WM_Ultra_Vanilla_Klipper ] && ! grep -qi 'Both ~/WM_Ultra' $MG/run2.log"
rm -rf "$MH/wm_ultra_vanilla_klipper" "$MH/WM_Ultra_Vanilla_Klipper"; cp -al "$ROOT" "$MH/WM_Ultra_Vanilla_Klipper"; cp -al "$ROOT" "$MH/wm_ultra_vanilla_klipper"
WM_TEST_PANEL_DIR="$T/stubpanel" WM_HOME="$MH" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$MH/WM_Ultra_Vanilla_Klipper/installer.sh" --update --only-addon webcam --webcam on > "$MG/run3.log" 2>&1
check "F-242 when both folders exist nothing is moved and the user is told" "[ -d $MH/WM_Ultra_Vanilla_Klipper/.git ] && [ ! -L $MH/WM_Ultra_Vanilla_Klipper ] && grep -q 'Both ~/WM_Ultra_Vanilla_Klipper and ~/wm_ultra_vanilla_klipper exist' $MG/run3.log"
check "F-242 the installer runs from the folder with the new name too" "bash $ROOT/installer.sh --version | grep -q 'wm_ultra_vanilla_klipper installer'"
check "F-242 README clone lines create the folder in lower case" "! grep -E 'git clone [^|]*WM_Ultra_Vanilla_Klipper(\\.git)?( &&|\$)' $ROOT/README.md $ROOT/README-DEVBOX.md"
check "update button: pi_update.sh is executable and valid bash" "[ -x $ROOT/scripts/pi_update.sh ] && bash -n $ROOT/scripts/pi_update.sh"
PU="$T/pu"; mkdir -p "$PU/wm-rpi-backup"; echo "VERSION=$(cat $ROOT/VERSION)" > "$PU/wm-rpi-backup/install.conf"
piu() { HOME="$PU" WM_PI_UPDATE_DELAY=0 WM_PI_UPDATE_SKIP_SUDO=1 WM_PI_UPDATE_CMD="echo ran >> $PU/ran" "$@" bash $ROOT/scripts/pi_update.sh; }
check "update button: same version as installed does nothing" "rm -f $PU/ran; WM_TEST_PRINT_STATE=standby piu env; [ ! -e $PU/ran ]"
printf 'VERSION=0.0.1\n' > "$PU/wm-rpi-backup/install.conf"
check "update button: a print running means the update is not applied, and the log says so" "rm -f $PU/ran; WM_TEST_PRINT_STATE=printing piu env; [ ! -e $PU/ran ] && grep -q 'a print is active (printing)' $PU/wm-pi-update.log"
check "update button: a newer folder version is applied (installer --update --yes command runs)" "rm -f $PU/ran; WM_TEST_PRINT_STATE=standby piu env; [ -e $PU/ran ] && grep -q 'applying the installer update 0.0.1' $PU/wm-pi-update.log"
check "update button: nothing installed yet means nothing happens" "rm -f $PU/ran; rm -f $PU/wm-rpi-backup/install.conf; WM_TEST_PRINT_STATE=standby piu env; [ ! -e $PU/ran ]"
sec "== update everything: Fluidd panel, screen boards, doctor"
mkdir -p "$PU/wm-ultra-fluidd-acepro-panel"; echo 9.9.9 > "$PU/wm-ultra-fluidd-acepro-panel/VERSION"
printf 'VERSION=%s\n' "$(cat $ROOT/VERSION)" > "$PU/wm-rpi-backup/install.conf"; rm -f "$PU/ran" "$PU/wm-pi-update.log"
pipanel() { HOME="$PU" WM_PI_UPDATE_DELAY=0 WM_PI_UPDATE_SKIP_SUDO=1 WM_PI_UPDATE_CMD="echo panel-ran >> $PU/ran" WM_TEST_PRINT_STATE="${1:-standby}" bash $ROOT/scripts/pi_update.sh --panel; }
check "panel update: not installed by this installer yet means nothing happens" "rm -f $PU/ran $PU/wm-rpi-backup/panel.version; pipanel; [ ! -e $PU/ran ] && grep -q 'was not installed by this installer yet' $PU/wm-pi-update.log"
echo 0.0.1 > "$PU/wm-rpi-backup/panel.version"
check "panel update: a print running means it is not applied" "rm -f $PU/ran; pipanel printing; [ ! -e $PU/ran ] && grep -q 'Fluidd panel update to 9.9.9 was NOT applied' $PU/wm-pi-update.log"
check "panel update: a newer panel folder is applied" "rm -f $PU/ran; pipanel; [ -e $PU/ran ] && grep -q 'applying the Fluidd panel update 0.0.1 -> 9.9.9' $PU/wm-pi-update.log"
echo 9.9.9 > "$PU/wm-rpi-backup/panel.version"
check "panel update: same version does nothing" "rm -f $PU/ran; pipanel; [ ! -e $PU/ran ]"
check "panel update: the command is the installer's acepro-only update" "grep -q -- '--only-addon acepro' $ROOT/scripts/pi_update.sh"
printf 'VERSION=0.0.1\n' > "$PU/wm-rpi-backup/install.conf"; printf 't13dp@10.0.0.9\n' > "$PU/wm-rpi-backup/boards.conf"
check "installer update: pi_update.sh no longer starts a second boards step (installer --update looks at the boards itself, only the ones that are behind)" "rm -f $PU/ran $PU/boards-ran; HOME=$PU WM_PI_UPDATE_DELAY=0 WM_PI_UPDATE_SKIP_SUDO=1 WM_TEST_PRINT_STATE=standby WM_PI_UPDATE_CMD='true' WM_PI_UPDATE_BOARDS_CMD='echo b >> $PU/boards-ran' bash $ROOT/scripts/pi_update.sh; [ ! -e $PU/boards-ran ] && ! grep -q update-boards $ROOT/scripts/pi_update.sh || grep -q '^# The screen boards you added: installer.sh --update looks' $ROOT/scripts/pi_update.sh"
mkdir -p "$HG/wm-ultra-fluidd-acepro-panel"; git -C "$HG/wm-ultra-fluidd-acepro-panel" init -q 2>/dev/null
inst "$HG" --update --only-addon webcam --webcam on >/dev/null
check "panel update: the watcher units are installed and enabled" "grep -q 'install -m 644 .*/etc/systemd/system/wm-panel-update.path' $HG/.sudo.log && grep -q 'systemctl enable --now wm-panel-update.path' $HG/.sudo.log"
check "panel update: the path unit watches the panel folder's git log, the service runs pi_update.sh --panel" "grep -q '^PathModified=.*/wm-ultra-fluidd-acepro-panel/.git/logs/HEAD' $HG/.wm-units/wm-panel-update.path && grep -q '^ExecStart=/bin/bash .*/scripts/pi_update.sh --panel' $HG/.wm-units/wm-panel-update.service"
check "panel update: both units are recorded for the uninstall" "grep -q 'wm-panel-update.path' $HG/wm-rpi-backup/installed.manifest && grep -q 'wm-panel-update.service' $HG/wm-rpi-backup/installed.manifest"
# screen boards over ssh (a fake ssh records what would run)
FS="$T/fakessh"; cat > "$FS" <<'FEOF'
#!/bin/bash
# fake ssh: -o options ... target command
while [ "${1:-}" = -o ]; do shift 2; done
t="$1"; shift; echo "$t $*" >> "${FAKE_SSH_LOG:-/dev/null}"
case "$*" in
    true) exit 0 ;;
    *wm-factory-restore*) echo "update handed over"; exit 0 ;;
    *wm-screen-backup/in_test*) [ "$t" = t13dp@10.0.0.9 ] && [ -f "${FAKE_BOARD_INTEST:-/nonexistent}" ] && echo yes; exit 0 ;;
    *wm-screen-backup/release*) [ "$t" = t13dp@10.0.0.9 ] && echo "${FAKE_BOARD_RELEASE:-}"; exit 0 ;;
    *wm-screen-backup/screen_version*) [ "$t" = t13dp@10.0.0.9 ] && echo "${FAKE_BOARD_VERSION:-S1.0.0}"; exit 0 ;;
    *"show -p Timezone"*) [ "$t" = t13dp@10.0.0.9 ] && echo "${FAKE_BOARD_TZ:-America/Toronto}"; exit 0 ;;
esac
exit 0
FEOF
chmod +x "$FS"; BH="$T/bh"; mkdir -p "$BH"; BL="$T/bh.sshlog"; : > "$BL"
binst() { FAKE_SSH_LOG="$BL" WM_SSH="$FS" WM_TEST_NO_FETCH=1 inst "$BH" "$@"; }
inst "$BH" --from-github --model ultra-s --screen off >/dev/null
check "2.34.0: --status lists the release of the Pi, the panel and each screen board, and says when they differ" "binst --board add t13dp@10.0.0.9 >/dev/null; mkdir -p $BH/wm-ultra-fluidd-acepro-panel; cp $ROOT/RELEASE $BH/wm-ultra-fluidd-acepro-panel/RELEASE; O=\$(FAKE_BOARD_RELEASE=0.0.1 binst --status); echo \"\$O\" | grep -q 'Pi installer:' && echo \"\$O\" | grep -q 'Screen board t13dp@10.0.0.9: *0.0.1 *<-- not the Pi release' && echo \"\$O\" | grep -q 'not all on the same release'"
check "2.34.0: --status says nothing is wrong when all three are on the same release" "O=\$(FAKE_BOARD_RELEASE=\$(head -n1 $ROOT/RELEASE) binst --status); ! echo \"\$O\" | grep -q 'not all on the same release' && echo \"\$O\" | grep -q 'Fluidd panel: *'\$(head -n1 $ROOT/RELEASE)"
check "2.34.0: a board with no release mark is reported" "O=\$(binst --status); echo \"\$O\" | grep -q 'Screen board t13dp@10.0.0.9: *no release mark'"
check "2.34.0: the screen board marks carry the release (write_screen_marks copies RELEASE)" "grep -q 'cp \"\$src/RELEASE\" \"\$BK/release\"' $ROOT/scripts/screen_board.sh"
binst --board remove t13dp@10.0.0.9 >/dev/null 2>&1; rm -rf $BH/wm-ultra-fluidd-acepro-panel
check "2.34.0: a screen board marked IN TEST is not updated by the Pi (--update-boards skips it and says how to turn the mark off)" "binst --board add t13dp@10.0.0.9 >/dev/null; : > $T/intest.flag; O=\$(FAKE_BOARD_INTEST=$T/intest.flag binst --update-boards); echo \"\$O\" | grep -q 'marked IN TEST: it is NOT updated' && ! grep -q wm-factory-restore $BL; binst --board remove t13dp@10.0.0.9 >/dev/null 2>&1"
check "2.34.0: --board test-on and test-off set and clear the mark on the board" "binst --board test-on t13dp@10.0.0.9 | grep -q 'marked IN TEST' && grep -q 'wm-screen-backup/in_test' $BL && binst --board test-off t13dp@10.0.0.9 | grep -q 'not in test any more'"
check "2.34.0: on the board, --update with the mark does nothing and says so; --force goes on; --in-test off clears it" "BD=$T/intestboard; mkdir -p \$BD; s() { WM_HOME=\$BD WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/scripts/screen_board.sh \"\$@\" 2>&1; }; s --in-test on >/dev/null; s --update | grep -q 'marked IN TEST' && ! s --update --force | grep -q 'marked IN TEST' && s --in-test off | grep -q 'not in test any more' && s --in-test status | grep -q 'not in test'"
check "boards: --board list says none at first" "binst --board list | grep -q 'No screen board added'"
check "boards: --board add needs user@address" "binst --board add 10.0.0.9 | grep -q 'user@address'"
check "boards: --board add saves it" "binst --board add t13dp@10.0.0.9 | grep -q 'added' && grep -qx 't13dp@10.0.0.9' $BH/wm-rpi-backup/boards.conf && binst --board list | grep -q 't13dp@10.0.0.9'"
check "boards: --board add without an address and no announced board explains" "binst --board add | grep -q 'no screen board address is known yet'"
mkdir -p $BH/printer_data/config; echo '{"url": "http://10.0.0.9:8765"}' > $BH/printer_data/config/rpi_chamber_light.json
check "boards: --board add without an address uses the board that announced itself" "binst --board add | grep -q 'Screen board found at 10.0.0.9' && grep -qx 't13dp@10.0.0.9' $BH/wm-rpi-backup/boards.conf"
check "boards: adding it twice keeps one line" "binst --board add t13dp@10.0.0.9 >/dev/null; [ \$(grep -c 't13dp@10.0.0.9' $BH/wm-rpi-backup/boards.conf) = 1 ]"
check "boards: --update-boards updates a board that is behind (runs the root copy with sudo -n)" "FAKE_BOARD_VERSION=S0.0.1 binst --update-boards | grep -q 'update started'; grep -q 'sudo -n /usr/local/sbin/wm-factory-restore --update --yes --detach' $BL"
check "boards: --update-boards leaves a board that is current alone" "BEFORE=\$(grep -c wm-factory-restore $BL); FAKE_BOARD_VERSION=S99.0.0 binst --update-boards | grep -q 'up to date'; [ \$(grep -c wm-factory-restore $BL) = \$BEFORE ]"
check "boards: --board add gives a board on China time the Pi's time zone" "FAKE_BOARD_TZ=Asia/Shanghai binst --board add t13dp@10.0.0.9 | grep -q 'time zone set to America/Toronto (was Asia/Shanghai)'; grep -q 'sudo -n timedatectl set-timezone America/Toronto' $BL"
check "boards: --update-boards sets the board's time zone also when the board is current" "BEFORE=\$(grep -c 'set-timezone' $BL); FAKE_BOARD_TZ=Asia/Shanghai FAKE_BOARD_VERSION=S99.0.0 binst --update-boards | grep -q 'time zone set to America/Toronto'; [ \$(grep -c 'set-timezone' $BL) -gt \$BEFORE ]"
check "boards: a board already on the Pi's time zone is left alone" "BEFORE=\$(grep -c 'set-timezone' $BL); FAKE_BOARD_VERSION=S99.0.0 binst --update-boards >/dev/null; [ \$(grep -c 'set-timezone' $BL) = \$BEFORE ]"
check "boards: --update-boards is refused during a print" "WM_TEST_PRINT_STATE=printing FAKE_BOARD_VERSION=S0.0.1 binst --update-boards | grep -q 'print is running'"
check "boards: a board that cannot be reached is reported, not forgotten" "binst --board add t13dp@10.9.9.9 >/dev/null; FAKE_BOARD_VERSION=S0.0.1 binst --update-boards | grep -q 'cannot be reached over ssh'"
check "boards: --board remove takes it out" "binst --board remove t13dp@10.9.9.9 >/dev/null; ! grep -q '10.9.9.9' $BH/wm-rpi-backup/boards.conf"
check "doctor: reports a board that is behind and offers the update" "FAKE_BOARD_VERSION=S0.0.1 WM_TEST_UPDATES=1 binst --doctor </dev/null | grep -q 'screen board t13dp@10.0.0.9 is behind'"
check "doctor: a board that is current is ok" "FAKE_BOARD_VERSION=S99.0.0 WM_TEST_UPDATES=1 binst --doctor </dev/null | grep -q 'screen board t13dp@10.0.0.9 has screen S99.0.0'"
check "--check-updates shows the boards and points to --update-all" "FAKE_BOARD_VERSION=S0.0.1 WM_TEST_NEW_VERSION=99.0.0 binst --check-updates | grep -q 'Screen board t13dp@10.0.0.9: installed screen S0.0.1'"
check "screen version: SCREEN_VERSION is S<n>.<n>.<n> and SCREEN_NEEDS_PI is a plain version not newer than VERSION" "grep -Eq '^S[0-9]+\\.[0-9]+\\.[0-9]+\$' $ROOT/SCREEN_VERSION && grep -Eq '^[0-9]+\\.[0-9]+\\.[0-9]+\$' $ROOT/SCREEN_NEEDS_PI && [ \"\$(printf '%s\\n%s\\n' \$(cat $ROOT/SCREEN_NEEDS_PI) \$(cat $ROOT/VERSION) | sort -V | tail -1)\" = \"\$(cat $ROOT/VERSION)\" ]"
check "versions: the Pi, Screen and Panel versions are saved in Moonraker's database, never by a test run" "sed -n '/^publish_versions()/,/^}/p' $ROOT/installer.sh | grep -q 'TESTING.*= 1.*return 0' && sed -n '/^publish_versions()/,/^}/p' $ROOT/installer.sh | grep -q 'namespace.*wondermaker.*versions' && grep -q '^    publish_versions' $ROOT/installer.sh"
check "screen version: the screen bundle holds SCREEN_VERSION and SCREEN_NEEDS_PI" "B=\$(mktemp -d); tar xzf $ROOT/screen_board_bundle/wm-screen-board.tar.gz -C \$B && cmp -s \$B/SCREEN_VERSION $ROOT/SCREEN_VERSION && cmp -s \$B/SCREEN_NEEDS_PI $ROOT/SCREEN_NEEDS_PI; r=\$?; rm -rf \$B; [ \$r = 0 ]"
check "screen version: a board that still reports an old Pi-style number (2.x) counts as behind and is updated" "FAKE_BOARD_VERSION=2.27.0 binst --update-boards | grep -q 'update started (screen 2.27.0 (before S1.0.0)'"
check "screen version: a board on the same screen version is left alone, even when the Pi version is newer" "BEFORE=\$(grep -c wm-factory-restore $BL); FAKE_BOARD_VERSION=\$(cat $ROOT/SCREEN_VERSION) binst --update-boards | grep -q 'up to date (screen'; [ \$(grep -c wm-factory-restore $BL) = \$BEFORE ]"
check "screen version: a screen update that needs a newer Pi than the installed one is skipped with the reason" "BEFORE=\$(grep -c wm-factory-restore $BL); FAKE_BOARD_VERSION=S0.0.1 WM_TEST_SCREEN_NEEDS_PI=99.0.0 binst --update-boards | grep -q 'needs this Pi on installer 99.0.0'; [ \$(grep -c wm-factory-restore $BL) = \$BEFORE ]"
check "screen version: --update ends by updating the boards that are behind" "BEFORE=\$(grep -c wm-factory-restore $BL); FAKE_BOARD_VERSION=S0.0.1 binst --update 2>&1 | grep -q 'update started (screen S0.0.1'; [ \$(grep -c wm-factory-restore $BL) -gt \$BEFORE ]"
check "screen version: --update leaves a board that is current alone" "BEFORE=\$(grep -c wm-factory-restore $BL); FAKE_BOARD_VERSION=S99.0.0 binst --update >/dev/null 2>&1; [ \$(grep -c wm-factory-restore $BL) = \$BEFORE ]"
check "screen version: --update during a print does not start a board update" "BEFORE=\$(grep -c wm-factory-restore $BL); WM_TEST_PRINT_STATE=printing FAKE_BOARD_VERSION=S0.0.1 binst --update >/dev/null 2>&1; [ \$(grep -c wm-factory-restore $BL) = \$BEFORE ]"
check "screen version: the screen's version reading understands S1.0.0 and ignores the old Pi-style marks" "python3 -c \"import sys; sys.path.insert(0,'$ROOT/zr_tools'); import zr_logic as L; assert L.version_tuple('S1.0.0')==(1,0,0) and L.version_newer('S1.1.0','S1.0.0') and not L.version_newer('S1.0.0','S1.0.0') and L.version_newer('S1.0.0','')\""
check "--update-all is refused during a print" "WM_TEST_PRINT_STATE=printing binst --update-all | grep -q 'print is running or paused'"
check "--help lists --update-all and --board" "bash $ROOT/installer.sh --help | grep -q -- '--update-all' && bash $ROOT/installer.sh --help | grep -q -- '--board add'"
check "webcam helper: python tests" "python3 -I -W ignore $ROOT/tests/test_crowsnest.py"
check "crowsnest.conf is the explained v5 file (every option, the manual link)" "grep -q 'mainsail-crew/crowsnest/blob/master/README.md' $HG/printer_data/config/crowsnest.conf && grep -q '^####  max_fps' $HG/printer_data/config/crowsnest.conf && grep -q '^\[cam 1\]' $HG/printer_data/config/crowsnest.conf && ! grep -q enable_rtsp $HG/printer_data/config/crowsnest.conf"
check "webcam: install adds [webcam Camera] to moonraker.conf" "grep -q '^\[webcam Camera\]' $HG/printer_data/config/moonraker.conf && grep -q 'stream_url: /webcam/?action=stream' $HG/printer_data/config/moonraker.conf"
check "webcam: answers are saved for --update" "grep -q '^CAM_COUNT=' $HG/wm-rpi-backup/install.conf && grep -q '^CAM_FPS=' $HG/wm-rpi-backup/install.conf"
WCH="$T/wch"; mkdir -p "$WCH"
WM_TEST_PI_MODEL="Raspberry Pi 5 Model B Rev 1.0" WM_TEST_CAMERAS='[{"kind":"usb","path":"/dev/v4l/by-id/usb-A-video-index0","name":"A"}]' inst "$WCH" --from-github --model ultra-s --screen off --cameras 3 --cam-resolution 1080p --cam-fps 25 >/dev/null
check "webcam: --cameras 3 --cam-resolution 1080p --cam-fps 25 are used (3 cams, ports 8080-8082, ustreamer on a Pi 5)" "[ \$(grep -c '^\[cam ' $WCH/printer_data/config/crowsnest.conf) = 3 ] && grep -q 'port: 8082' $WCH/printer_data/config/crowsnest.conf && grep -q 'resolution: 1920x1080' $WCH/printer_data/config/crowsnest.conf && grep -q 'max_fps: 25' $WCH/printer_data/config/crowsnest.conf && grep -q 'mode: ustreamer' $WCH/printer_data/config/crowsnest.conf && ! grep -q 'camera-streamer$' $WCH/printer_data/config/crowsnest.conf"
check "webcam: Fluidd gets Camera, Camera 2, Camera 3" "( for n in 'Camera' 'Camera 2' 'Camera 3'; do grep -q \"^\[webcam \$n\]\" $WCH/printer_data/config/moonraker.conf || exit 1; done; grep -q '/webcam3/?action=snapshot' $WCH/printer_data/config/moonraker.conf )"
check "webcam (F-191): the streamer is ustreamer by default, also on a Pi 4; --cam-mode camera-streamer gives camera-streamer" "WCP=$T/wcp; mkdir -p \$WCP; WM_TEST_PI_MODEL='Raspberry Pi 4 Model B Rev 1.4' inst \$WCP --from-github --model ultra-s --screen off >/dev/null; grep -q 'mode: ustreamer' \$WCP/printer_data/config/crowsnest.conf && ! grep -q 'mode: camera-streamer' \$WCP/printer_data/config/crowsnest.conf; WCP2=$T/wcp2; mkdir -p \$WCP2; WM_TEST_PI_MODEL='Raspberry Pi 4 Model B Rev 1.4' inst \$WCP2 --from-github --model ultra-s --screen off --cam-mode camera-streamer >/dev/null; grep -q 'mode: camera-streamer' \$WCP2/printer_data/config/crowsnest.conf"
check "webcam: a bad --cam-fps stops with a fix" "mkdir -p $T/wcbad; inst $T/wcbad --screen off --cam-fps 99 | grep -q 'max_fps must be'"
WCK="$T/wck"; mkdir -p "$WCK"; inst "$WCK" --from-github --model ultra-s --screen off >/dev/null
printf '[cam mine]\nmode: ustreamer\nport: 8080\ndevice: /dev/video9\n' > "$WCK/printer_data/config/crowsnest.conf"; rm -rf "$WCK/crowsnest"
inst "$WCK" --update --only-addon webcam --webcam on >/dev/null
check "webcam: an existing crowsnest.conf is never overwritten; the explained copy is crowsnest.conf.new" "grep -q 'device: /dev/video9' $WCK/printer_data/config/crowsnest.conf && ! grep -q 'Written by the WM_Ultra' $WCK/printer_data/config/crowsnest.conf && grep -q 'Written by the WM_Ultra' $WCK/printer_data/config/crowsnest.conf.new"
check "webcam: --webcam-setup rewrites the conf, keeps a copy, adds Camera 2" "inst $WCK --webcam-setup --cameras 2 --cam-resolution 480p --cam-fps 10 >/dev/null; [ \$(grep -c '^\[cam ' $WCK/printer_data/config/crowsnest.conf) = 2 ] && grep -q 'resolution: 640x480' $WCK/printer_data/config/crowsnest.conf && grep -q 'device: /dev/video9' $WCK/printer_data/config/crowsnest.conf.wm-before-webcam-setup-* && grep -q '^\[webcam Camera 2\]' $WCK/printer_data/config/moonraker.conf"
WCR="$T/wcr"; mkdir -p "$WCR"; inst "$WCR" --from-github --model ultra-s --screen off >/dev/null
printf '[cam 1]\nmode: ustreamer\nport: 8080\ndevice: /dev/video1\n[cam 2]\nmode: ustreamer\nport: 8081\ndevice: /dev/video2\n' > "$WCR/printer_data/config/crowsnest.conf"; rm -rf "$WCR/crowsnest"; : > "$WCR/.sudo.log"
check "webcam: a new [webcam Camera 2] restarts Moonraker so Fluidd lists it (F-135)" "inst $WCR --update --only-addon webcam --webcam on --cameras 2 >/dev/null; grep -q '^\[webcam Camera 2\]' $WCR/printer_data/config/moonraker.conf && grep -q 'restart moonraker' $WCR/.sudo.log"
check "webcam: --webcam-setup without the service installed says how to install it" "inst $T/wcbad --webcam-setup | grep -q 'not installed'"
check "webcam: --dry-run --webcam-setup changes nothing" "inst $WCK --dry-run --webcam-setup --cameras 3 | grep -q 'would rewrite crowsnest.conf (3 camera' && [ \$(grep -c '^\[cam ' $WCK/printer_data/config/crowsnest.conf) = 2 ]"
# B-060: "Set up the cameras again" in the menu must ask again, even when earlier answers (1 camera) were saved, and a second camera must be written
WCQ="$T/wcq"; mkdir -p "$WCQ"; inst "$WCQ" --from-github --model ultra-s --screen off --cameras 1 --cam-resolution 1080p --cam-fps 30 >/dev/null
check "webcam: --webcam-setup asks the questions again after 1 camera was saved, and writes the second camera (B-060)" "printf '2\\n1\\n10\\ny\\n' | WM_TEST_CAMERAS='[{\"kind\":\"usb\",\"path\":\"/dev/v4l/by-id/usb-A-video-index0\",\"name\":\"A\"},{\"kind\":\"usb\",\"path\":\"/dev/v4l/by-id/usb-B-video-index0\",\"name\":\"B\"}]' WM_HOME=$WCQ WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --webcam-setup >/dev/null 2>&1; [ \$(grep -c '^\[cam ' $WCQ/printer_data/config/crowsnest.conf) = 2 ] && grep -q '^\[webcam Camera 2\]' $WCQ/printer_data/config/moonraker.conf"

sec "== camera on the screen board (the factory camera plugs into the screen board)"
SCP="$T/scp"; mkdir -p "$SCP/printer_data/config"; echo '{"url": "http://board-1.local:8080"}' > "$SCP/printer_data/config/rpi_screen_camera.json"; cp "$ROOT/config/nginx_upstreams.conf" "$T/scp_up.conf"
WM_NGINX_UPSTREAMS="$T/scp_up.conf" inst "$SCP" --from-github --model ultra-s --screen off --cameras 1 --cam-resolution 720p --cam-fps 30 > "$T/scp.out"
check "screen camera: the question is not asked without a terminal, the answer yes is saved" "grep -q '^SCREEN_CAM=yes' $SCP/wm-rpi-backup/install.conf"
check "screen camera: this Pi's cameras start at [cam 2] on port 8081" "grep -q '^\[cam 2\]' $SCP/printer_data/config/crowsnest.conf && ! grep -q '^\[cam 1\]' $SCP/printer_data/config/crowsnest.conf && grep -q '^port: 8081' $SCP/printer_data/config/crowsnest.conf"
check "screen camera: Fluidd gets Camera (the board) and Camera 2 (this Pi)" "grep -q '^\[webcam Camera\]' $SCP/printer_data/config/moonraker.conf && grep -q '^\[webcam Camera 2\]' $SCP/printer_data/config/moonraker.conf && grep -q 'stream_url: /webcam/?action=stream' $SCP/printer_data/config/moonraker.conf"
check "screen camera: nginx /webcam/ goes to the board, the other ports stay" "grep -q 'mjpgstreamer1 { server board-1.local:8080; }' $T/scp_up.conf && grep -q 'mjpgstreamer2 { server 127.0.0.1:8081; }' $T/scp_up.conf"
check "screen camera: a second run changes nothing" "cp $T/scp_up.conf $T/scp_up.before; WM_NGINX_UPSTREAMS=$T/scp_up.conf inst $SCP --update --only-addon webcam --webcam on >/dev/null; cmp -s $T/scp_up.conf $T/scp_up.before && [ \$(grep -c '^\[webcam Camera\]' $SCP/printer_data/config/moonraker.conf) = 1 ]"
check "screen camera: 0 cameras on the Pi builds no webcam service, the screen camera still works" "SC0=$T/sc0; mkdir -p \$SC0/printer_data/config; cp $SCP/printer_data/config/rpi_screen_camera.json \$SC0/printer_data/config/; cp $ROOT/config/nginx_upstreams.conf $T/sc0_up.conf; WM_NGINX_UPSTREAMS=$T/sc0_up.conf inst \$SC0 --from-github --model ultra-s --screen off --cameras 0 >/dev/null; [ ! -d \$SC0/crowsnest ] && grep -q '^\[webcam Camera\]' \$SC0/printer_data/config/moonraker.conf && grep -q 'server board-1.local:8080' $T/sc0_up.conf && ! grep -q '^\[webcam Camera 2\]' \$SC0/printer_data/config/moonraker.conf"
check "screen camera: 4 cameras on the Pi are refused (the board takes one of the four)" "S4=$T/sc4; mkdir -p \$S4/printer_data/config; cp $SCP/printer_data/config/rpi_screen_camera.json \$S4/printer_data/config/; inst \$S4 --from-github --model ultra-s --screen off --cameras 4 | grep -q 'number of cameras'"
check "screen camera: --webcam-setup --screen-camera no gives /webcam/ back to this Pi" "WM_NGINX_UPSTREAMS=$T/scp_up.conf inst $SCP --webcam-setup --screen-camera no --cameras 1 --cam-resolution 720p --cam-fps 30 >/dev/null; grep -q 'mjpgstreamer1 { server 127.0.0.1:8080; }' $T/scp_up.conf && grep -q '^\[cam 1\]' $SCP/printer_data/config/crowsnest.conf && grep -q '^SCREEN_CAM=no' $SCP/wm-rpi-backup/install.conf"
SCN="$T/scn"; mkdir -p "$SCN/printer_data/config"; cp "$ROOT/config/nginx_upstreams.conf" "$T/scn_up.conf"
WM_NGINX_UPSTREAMS="$T/scn_up.conf" inst "$SCN" --from-github --model ultra-s --screen off --cameras 1 >/dev/null
check "screen camera: no camera announced means no question, cameras as before (Camera on this Pi, /webcam/ unchanged)" "grep -q '^SCREEN_CAM=no' $SCN/wm-rpi-backup/install.conf && grep -q '^\[cam 1\]' $SCN/printer_data/config/crowsnest.conf && grep -q 'mjpgstreamer1 { server 127.0.0.1:8080; }' $T/scn_up.conf"
check "screen camera: --screen-camera yes without an announced camera is refused with the fix" "inst $SCN --webcam-setup --screen-camera yes --cameras 1 | grep -q 'announced a camera yet'"
check "screen camera: an existing crowsnest.conf with a camera on 8080 gets a warning" "printf '[cam 1]\nmode: ustreamer\nport: 8080\ndevice: /dev/video9\n' > $SCP/printer_data/config/crowsnest.conf; WM_NGINX_UPSTREAMS=$T/scp_up.conf inst $SCP --update --only-addon webcam --webcam on --screen-camera yes | grep -q 'camera on port 8080'"
sec "== model is applied to every source"
H8="$T/h8"; mkdir -p "$H8"; echo "[include zru-s.cfg]" >> "$T/src_home/printer_data/config/printer.cfg"; mkstage "$T/stage_s"; echo "[include zru-s.cfg]" >> "$T/src_home/printer_data/config/printer.cfg"; tar czf "$T/stage_s/data.tgz" -C "$T/src_home" --exclude=printer_data/gcodes printer_data fluidd TM_T1
inst "$H8" --from-stage "$T/stage_s" --model ultra > /dev/null
check "ultra chosen with a stage that has zru-s on: switched off, backup kept" "grep -q '^# \\[include zru-s.cfg\\]' $H8/printer_data/config/printer.cfg && [ -f $H8/printer_data/config/printer.cfg.wm-model-bak ]"
H9="$T/h9"; mkdir -p "$H9"; inst "$H9" --from-stage "$T/stage_s" --model ultra-s > /dev/null
check "ultra-s chosen: zru-s on" "grep -q '^\\[include zru-s.cfg\\]' $H9/printer_data/config/printer.cfg && [ \"\$(cat $H9/printer_data/wm-model)\" = ultra-s ]"
H10="$T/h10"; mkdir -p "$H10"; printf '1\ny\ny\ny\nn\ny\n' | WM_HOME="$H10" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --from-github > "$T/ask.out" 2>&1
check "installer asks for the model when not given" "grep -q 'Which printer do you have' $T/ask.out && [ \"\$(cat $H10/printer_data/wm-model)\" = ultra ]"

sec "== first start, checks, canbus_uuid"
printf 'Found canbus_uuid=000000000000, Application: Klipper\nFound canbus_uuid=000000000001, Application: Klipper\n' > "$T/can_ok.txt"
printf 'Found canbus_uuid=bb1122334455, Application: Klipper\nFound canbus_uuid=000000000001, Application: Klipper\n' > "$T/can_new.txt"
G1="$T/g1"; mkdir -p "$G1"; inst "$G1" --from-github --model ultra-s > "$T/g1.out"
check "install with no CAN answer: services still enabled and started, problem reported" "grep -q 'systemctl enable klipper' $G1/.sudo.log && grep -q 'systemctl restart klipper' $G1/.sudo.log && grep -q 'enabled anyway' $T/g1.out"
check "install says how to continue" "grep -q 'first-start' $T/g1.out"
check "klipper never started before the final step" "[ \$(grep -c 'restart klipper' $G1/.sudo.log) = 1 ]"
check "answers saved" "grep -q '^MODEL=ultra-s' $G1/wm-rpi-backup/install.conf && grep -q '^WANT_CROWSNEST=1' $G1/wm-rpi-backup/install.conf"
check "plan shown before changes" "grep -q 'Plan (nothing has been changed yet)' $T/g1.out"
check "pre-flight ran" "grep -q 'Pre-flight checks' $T/g1.out"
G2="$T/g2"; mkdir -p "$G2"; WM_TEST_CANQUERY="$T/can_ok.txt" inst "$G2" --from-github --model ultra-s > "$T/g2.out"
check "everything passes: klipper enabled and started" "grep -q 'systemctl enable klipper' $G2/.sudo.log && grep -q 'systemctl restart klipper' $G2/.sudo.log"
check "moonraker and nginx enabled at the end" "grep -q 'systemctl enable nginx' $G2/.sudo.log"
G3="$T/g3"; mkdir -p "$G3"; WM_TEST_CANQUERY="$T/can_ok.txt" inst "$G3" --from-github --model ultra-s --no-start > /dev/null
check "--no-start keeps klipper off" "! grep -Eq 'systemctl (start|restart|enable) klipper' $G3/.sudo.log"
G4="$T/g4"; mkdir -p "$G4"; WM_TEST_BRIDGE=0 WM_TEST_CANQUERY="$T/can_ok.txt" inst "$G4" --from-github --model ultra-s > "$T/g4.out"
check "no USB bridge: reason shown" "grep -q 'no main board on USB' $T/g4.out"
check "--first-start alone does not start klipper when a check fails" "! WM_TEST_BRIDGE=0 WM_TEST_CANQUERY=$T/can_ok.txt WM_HOME=$G3 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --first-start && ! grep -Eq 'systemctl (start|restart|enable) klipper' $G3/.sudo.log"
G5="$T/g5"; mkdir -p "$G5"; WM_TEST_CANQUERY="$T/can_new.txt" inst "$G5" --from-github --model ultra-s > "$T/g5.out"
check "new main board: canbus_uuid changed" "grep -q 'canbus_uuid: bb1122334455' $G5/printer_data/config/wm_zru_mcu.cfg"
check "old file kept before the change" "grep -q '000000000000' $G5/wm-rpi-backup/uuid-*/wm_zru_mcu.cfg"
check "hub uuid left alone" "grep -q '000000000001' $G5/printer_data/config/wm_zru_hub.cfg"
check "klipper started after the uuid fix" "grep -q 'systemctl restart klipper' $G5/.sudo.log"
# ---- CAN ids of the hub, extruder board, T0-T3 and the load cell: checked, offered a fix, set by hand (--can-ids, Doctor, first start)
G7="$T/g7"; mkdir -p "$G7"; WM_TEST_CANQUERY="$T/can_ok.txt" inst "$G7" --from-github --model ultra-s --no-start >/dev/null
C7="$G7/printer_data/config"; T2OLD="$(awk '/canbus_uuid/{print $2}' $C7/wm_zru_thr2.cfg)"; T1OLD="$(awk '/canbus_uuid/{print $2}' $C7/wm_zru_thr1.cfg)"
(awk '/canbus_uuid/{print $2}' $C7/wm_zru_*.cfg | grep -vx "$T2OLD"; echo ac9999999999) | sed 's/^/Found canbus_uuid=/; s/$/, Application: Klipper/' > "$T/can_t2.txt"
(awk '/canbus_uuid/{print $2}' $C7/wm_zru_*.cfg | grep -vx -e "$T2OLD" -e "$T1OLD"; echo ac9999999999; echo ac8888888888) | sed 's/^/Found canbus_uuid=/; s/$/, Application: Klipper/' > "$T/can_t12.txt"
cp -r "$C7" "$T/c7-orig"
check "doctor says which board's id is not on the bus (answers n: nothing changed)" "yes n 2>/dev/null | WM_TEST_CANQUERY=$T/can_t2.txt WM_HOME=$G7 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'toolhead T2 has $T2OLD in the config, which is not on the CAN bus' && grep -q $T2OLD $C7/wm_zru_thr2.cfg"
WM_TEST_CANQUERY="$T/can_t12.txt" WM_HOME="$G7" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --can-ids > "$T/canids0.out" 2>&1
check "two boards wrong and two unknown ids on the bus: unattended it does not guess" "grep -q 'cannot tell which is which' $T/canids0.out && grep -q $T2OLD $C7/wm_zru_thr2.cfg && grep -q $T1OLD $C7/wm_zru_thr1.cfg"
WM_TEST_CANQUERY="$T/can_t2.txt" WM_HOME="$G7" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --can-ids > "$T/canids1.out" 2>&1
check "--can-ids lists each board and whether it answers" "grep -q 'toolhead T2 .*NOT on the bus' $T/canids1.out && grep -q 'toolhead T0 .*answers' $T/canids1.out"
check "one board wrong and one unknown id on the bus: it takes the id, keeps a copy" "grep -q ac9999999999 $C7/wm_zru_thr2.cfg && ls $G7/wm-rpi-backup/uuid-*/wm_zru_thr2.cfg >/dev/null && grep -q $T2OLD $G7/wm-rpi-backup/uuid-*/wm_zru_thr2.cfg"
check "the other boards' files were not touched" "for f in mcu hub ext thr0 thr1 thr3 load_cell; do cmp -s $C7/wm_zru_\$f.cfg $T/c7-orig/wm_zru_\$f.cfg || exit 1; done"
WM_TEST_CANQUERY="$T/can_t2.txt" WM_HOME="$G7" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --can-ids > "$T/canids2.out" 2>&1
check "--can-ids says all fine when every id answers" "grep -q 'Every id in the config answers' $T/canids2.out"
check "--can-ids set T1 writes the id (lower case) and keeps a copy" "WM_HOME=$G7 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --can-ids set T1 AABBCCDDEEFF >/dev/null 2>&1 && grep -qx 'canbus_uuid: aabbccddeeff' $C7/wm_zru_thr1.cfg"
check "--can-ids set refuses an unknown board name and a bad id" "! WM_HOME=$G7 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --can-ids set T9 aabbccddeeff >/dev/null 2>&1 && ! WM_HOME=$G7 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --can-ids set T1 xyz >/dev/null 2>&1 && grep -qx 'canbus_uuid: aabbccddeeff' $C7/wm_zru_thr1.cfg"
sec "== CAN boards found by their firmware name (2.20.0), Extruder Setup is forced"
CM="$T/cm"; mkdir -p "$CM"
fw() { printf '"%s":["Klipper","%s"]' "$1" "$2"; }
{ echo '{'; fw aa0000000001 KLP_MCU_WM_ZRU_20260408_185504; echo ,; fw ae0000000002 KLP_HUB_WM_ZRU_20251114_151549; echo ,; fw ad0000000003 KLP_EXT_WM_ZRU_20251114_151429; echo ,; fw af0000000004 KLP_CELL_WM_ZRU_RPI_V2_20261117; echo ,
  fw ac0000000009 KLP_THR_WM_ZRU_20251114_151129; echo ,; fw ac0000000007 KLP_THR_WM_ZRU_20251114_151129; echo ,; fw ac0000000005 KLP_THR_WM_ZRU_20251114_151129; echo ,; fw ac0000000008 KLP_THR_WM_ZRU_20251114_151129; echo '}'; } > "$CM/ok.json"
mkcfg() { rm -rf "$1"; mkdir -p "$1"; local n; for n in mcu hub ext load_cell thr0 thr1 thr2 thr3; do printf '[mcu X]\ncanbus_uuid: b00000000000\n' > "$1/wm_zru_$n.cfg"; done; }
mkcfg "$CM/cfg"
check "canmatch: all 8 boards found, exit 0, nothing written without --apply" "WM_CANMATCH_FAKE=$CM/ok.json python3 $ROOT/scripts/wm_canmatch.py run --config-dir $CM/cfg --backup-dir $CM/bk > $CM/o1.txt && grep -q 'RESULT ok' $CM/o1.txt && ! grep -q aa0000000001 $CM/cfg/wm_zru_mcu.cfg"
check "canmatch: the load cell with the V2 name is told apart (KLP_CELL), the four KLP_THR are tool heads" "grep -q 'af0000000004.*load cell board' $CM/o1.txt && [ \$(grep -c 'tool head' $CM/o1.txt) = 4 ]"
check "canmatch --apply: main, hub, ext and load cell get their own id" "WM_CANMATCH_FAKE=$CM/ok.json python3 $ROOT/scripts/wm_canmatch.py run --config-dir $CM/cfg --backup-dir $CM/bk --apply >/dev/null && grep -q 'aa0000000001' $CM/cfg/wm_zru_mcu.cfg && grep -q 'ae0000000002' $CM/cfg/wm_zru_hub.cfg && grep -q 'ad0000000003' $CM/cfg/wm_zru_ext.cfg && grep -q 'af0000000004' $CM/cfg/wm_zru_load_cell.cfg"
check "canmatch --apply: the four tool heads are written in id order" "grep -q ac0000000005 $CM/cfg/wm_zru_thr0.cfg && grep -q ac0000000007 $CM/cfg/wm_zru_thr1.cfg && grep -q ac0000000008 $CM/cfg/wm_zru_thr2.cfg && grep -q ac0000000009 $CM/cfg/wm_zru_thr3.cfg"
check "canmatch --apply: the copies of the old files are OUTSIDE the config folder (tools that read every file there must not find them)" "[ -f $CM/bk/wm_zru_thr0.cfg ] && grep -q b00000000000 $CM/bk/wm_zru_thr0.cfg && [ \$(ls $CM/cfg | wc -l) = 8 ]"
mkcfg "$CM/cfg2"; sed 's/"ae0000000002":\["Klipper","KLP_HUB_WM_ZRU_20251114_151549"\],\?//' "$CM/ok.json" | tr -d '\n' | sed 's/,,/,/; s/,}/}/' > "$CM/nohub.json"
check "canmatch: a missing board (no hub) is reported, exit 1, nothing written" "! WM_CANMATCH_FAKE=$CM/nohub.json python3 $ROOT/scripts/wm_canmatch.py run --config-dir $CM/cfg2 --backup-dir $CM/bk2 --apply > $CM/o2.txt; grep -q 'RESULT unclear' $CM/o2.txt && grep -q 'hub: 0 found' $CM/o2.txt && grep -q b00000000000 $CM/cfg2/wm_zru_mcu.cfg"
printf '{"aa0000000001":["Klipper","KLP_MCU_X"],"aa0000000009":["Klipper","KLP_MCU_X"],"ae0000000002":["Klipper","KLP_HUB_X"],"ad0000000003":["Klipper","KLP_EXT_X"],"af0000000004":["Klipper","KLP_CELL_X"],"ac0000000001":["Klipper","KLP_THR_X"],"ac0000000002":["Klipper","KLP_THR_X"],"ac0000000003":["Klipper","KLP_THR_X"],"ac0000000004":["Klipper","KLP_THR_X"]}' > "$CM/two_main.json"
check "canmatch: two main boards on the bus: not guessed, nothing written" "! WM_CANMATCH_FAKE=$CM/two_main.json python3 $ROOT/scripts/wm_canmatch.py run --config-dir $CM/cfg2 --backup-dir $CM/bk2 --apply > $CM/o3.txt; grep -q 'main board: 2 found' $CM/o3.txt && grep -q b00000000000 $CM/cfg2/wm_zru_mcu.cfg"
printf '{"af0000000004":["Katapult",null],"aa0000000001":["Klipper","KLP_MCU_X"]}' > "$CM/boot.json"
check "canmatch: a board that only answers from its bootloader is not guessed" "! WM_CANMATCH_FAKE=$CM/boot.json python3 $ROOT/scripts/wm_canmatch.py run --config-dir $CM/cfg2 --backup-dir $CM/bk2 --apply > $CM/o4.txt; grep -q 'only the bootloader' $CM/o4.txt && grep -q 'RESULT unclear' $CM/o4.txt"
echo '{}' > "$CM/empty.json"
check "canmatch: nothing on the bus gives exit 2" "WM_CANMATCH_FAKE=$CM/empty.json python3 $ROOT/scripts/wm_canmatch.py run --config-dir $CM/cfg2 --backup-dir $CM/bk2 > $CM/o5.txt; [ \$? = 2 ] && grep -q 'RESULT none' $CM/o5.txt"
check "the load cell lookup only reads real *.cfg files (a copy of the old file next to it holds the old id)" "grep -q \"mcu CELL.*cell_uuid\\|cell_uuid()\" $ROOT/installer.sh && grep -A3 'cell_uuid() ' $ROOT/installer.sh | grep -qF -e \"--include='*.cfg'\""
# the installer: first start finds the boards by firmware name, then Extruder Setup is forced
(for u in aa0000000001 ae0000000002 ad0000000003 af0000000004 ac0000000009 ac0000000007 ac0000000005 ac0000000008; do echo "Found canbus_uuid=$u, Application: Klipper"; done) > "$CM/bus8.txt"
cmrun() { WM_TEST_CANQUERY="$CM/bus8.txt" WM_TEST_CANMATCH="$CM/ok.json" "$@"; }
G12="$T/g12"; mkdir -p "$G12"; inst "$G12" --from-github --model ultra-s --no-start >/dev/null; C12="$G12/printer_data/config"
check "no WM_TEST_CANMATCH: the old behaviour is unchanged (placeholders reported)" "WM_TEST_CANQUERY=$CM/bus8.txt WM_HOME=$G12 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --first-start 2>&1 | grep -q 'placeholder CAN id\\|not on the bus'"
cmrun env WM_HOME="$G12" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --first-start > "$T/cm1.out" 2>&1
check "first start: finds the boards by firmware name and writes all ids" "grep -q 'found by its firmware name' $T/cm1.out && grep -q aa0000000001 $C12/wm_zru_mcu.cfg && grep -q af0000000004 $C12/wm_zru_load_cell.cfg && grep -q ac0000000005 $C12/wm_zru_thr0.cfg"
check "first start: copies of the old files are in the backup folder, not in the config folder" "ls $G12/wm-rpi-backup/uuid-*/wm_zru_thr0.cfg >/dev/null && ! ls $C12 | grep -q 'wm_zru_thr0.cfg\\.'"
check "first start: Extruder Setup could not be run unattended: it says so and stays pending" "grep -q 'Extruder Setup was NOT done' $T/cm1.out && [ -f $G12/printer_data/.wm-extruder-setup-pending ]"
check "doctor reports the pending Extruder Setup" "WM_HOME=$G12 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor < /dev/null 2>&1 | grep -q 'Extruder Setup has not been done'"
WM_TEST_MATCH=stop WM_TEST_MATCH_ARG="After the pick of T1 no dock sensor shows an empty dock." WM_HOME="$G12" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --extruder-setup > "$T/cm2.out" 2>&1
check "--extruder-setup: a stopped run says why, writes nothing, stays pending" "grep -q 'did not finish: After the pick of T1' $T/cm2.out && [ -f $G12/printer_data/.wm-extruder-setup-pending ] && grep -q ac0000000005 $C12/wm_zru_thr0.cfg"
check "--extruder-setup: the warning to look at the printer and the docks is always shown" "grep -q 'IMPORTANT: look at the printer now' $T/cm2.out && grep -q 'All four tool heads must hang in their docks' $T/cm2.out"
WM_TEST_MATCH=apply WM_TEST_MATCH_ARG="ID0=ac0000000008 ID1=ac0000000009 ID2=ac0000000005 ID3=ac0000000007" WM_HOME="$G12" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --extruder-setup > "$T/cm3.out" 2>&1
check "--extruder-setup: the dock order found by the printer is written into thr0..thr3, then it is done" "grep -q ac0000000008 $C12/wm_zru_thr0.cfg && grep -q ac0000000009 $C12/wm_zru_thr1.cfg && grep -q ac0000000005 $C12/wm_zru_thr2.cfg && grep -q ac0000000007 $C12/wm_zru_thr3.cfg && grep -q 'dock order now' $T/cm3.out && [ ! -f $G12/printer_data/.wm-extruder-setup-pending ]"
WM_TEST_MATCH=same WM_HOME="$G12" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --extruder-setup > "$T/cm4.out" 2>&1
check "--extruder-setup: every tool came out of its own dock: nothing changes, done" "grep -q 'own dock: the ids are right' $T/cm4.out && [ ! -f $G12/printer_data/.wm-extruder-setup-pending ] && grep -q ac0000000008 $C12/wm_zru_thr0.cfg"
python3 - "$T/store.json" <<'PYE'
import json, sys, time
now = time.time() + 5
msgs = ["_WM_MATCH_RUN", "// action:prompt_text T0: x -> y",
        "// action:prompt_button Apply and restart|_WM_MATCH_APPLY ID0=ac000000000a ID1=ac000000000b ID2=ac000000000c ID3=ac000000000d|primary"]
json.dump({"result": {"gcode_store": [{"time": now, "type": "command", "message": m} for m in msgs]}}, open(sys.argv[1], "w"))
PYE
WM_TEST_STORE="$T/store.json" WM_HOME="$G12" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --extruder-setup > "$T/cm5.out" 2>&1
check "--extruder-setup: the ids are read from Fluidd's real button line (it ends in |primary) and written to the files (the first install test wrote nothing)" "grep -q ac000000000a $C12/wm_zru_thr0.cfg && grep -q ac000000000d $C12/wm_zru_thr3.cfg && ! grep -q 'primary' $C12/wm_zru_thr3.cfg && grep -q 'dock order now' $T/cm5.out"
python3 - "$T/store2.json" <<'PYE'
import json, sys, time
now = time.time() + 5
msgs = ["_WM_MATCH_RUN", "// action:prompt_button Apply and restart|_WM_MATCH_APPLY ID0=ac000000000a ID1=ac000000000a ID2=ac000000000c ID3=ac000000000d|primary"]
json.dump({"result": {"gcode_store": [{"time": now, "type": "command", "message": m} for m in msgs]}}, open(sys.argv[1], "w"))
PYE
WM_TEST_STORE="$T/store2.json" WM_HOME="$G12" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --extruder-setup > "$T/cm6.out" 2>&1
check "--extruder-setup: when the ids were refused (two the same) it does not say done, says the ids were NOT written and stays pending" "grep -q 'ids were NOT written' $T/cm6.out && ! grep -q 'dock order now' $T/cm6.out && [ -f $G12/printer_data/.wm-extruder-setup-pending ]"
check "the installer README and header list --extruder-setup" "grep -q -- '--extruder-setup' $ROOT/README.md && grep -q -- '--extruder-setup' $ROOT/installer.sh"
G6="$T/g6"; mkdir -p "$G6"; WM_TEST_CANQUERY="$T/can_ok.txt" inst "$G6" --from-github --model ultra-s --no-start >/dev/null
sed -i 's/^\[include zru-s.cfg\]/# [include zru-s.cfg]/' "$G6/printer_data/config/printer.cfg"
check "validator: ultra-s with zru-s off is an error" "! WM_TEST_CANQUERY=$T/can_ok.txt WM_HOME=$G6 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --first-start"
rm "$G6/printer_data/config/macros.cfg" 2>/dev/null; sed -i 's/^# \[include zru-s.cfg\]/[include zru-s.cfg]/' "$G6/printer_data/config/printer.cfg"
check "validator: missing include is an error" "! WM_TEST_CANQUERY=$T/can_ok.txt WM_HOME=$G6 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --first-start"
check "--hw-test changes nothing and lists the checks" "WM_TEST_CANQUERY=$T/can_ok.txt WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --hw-test | grep -q 'main board found on USB'"

sec "== print guard"
check "update refused while printing" "! WM_TEST_PRINT_STATE=printing WM_HOME=$G2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --repair"
check "--force goes on" "WM_TEST_PRINT_STATE=printing WM_HOME=$G2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --repair --force"

sec "== backup, restore"
WM_HOME="$G2" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --backup "$T/bk" >/dev/null 2>&1
BK="$(ls $T/bk/wm-backup-*.tgz | head -1)"
check "backup file made, private" "[ -f $BK ] && [ \"\$(stat -c %a $BK)\" = 600 ]"
check "backup holds config" "tar tzf $BK | grep -q printer_data/config/printer.cfg"
check "backup holds no gcodes or logs" "! tar tzf $BK | grep -Eq 'gcodes|logs/'"
echo "# changed" >> "$G2/printer_data/config/printer.cfg"
printf 'y\n' | WM_HOME="$G2" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --restore "$BK" >/dev/null 2>&1
check "restore brings the config back" "! grep -q '^# changed' $G2/printer_data/config/printer.cfg"
check "restore made a safety copy" "ls $G2/ultra-backup/settings/wm-backup-*.tgz"
check "restore refuses a wrong file" "! WM_HOME=$G2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --restore $T/ans"
mkdir -p "$G2/ultra-backup/settings"; cp "$BK" "$G2/ultra-backup/settings/wm-backup-test-before-update-20990101-000000.tgz"
echo "# changed after the update" >> "$G2/printer_data/config/printer.cfg"
check "2.25.0 (F-222): --rollback restores the newest backup from before an update" "printf 'y\\n' | WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --rollback 2>&1 | grep -q 'Restored from' && ! grep -q 'changed after the update' $G2/printer_data/config/printer.cfg"
check "2.25.0 (F-222): --rollback with no backup from before an update stops with a fix" "! WM_HOME=$T/norb WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --rollback 2>&1 | grep -q 'Restored from' && WM_HOME=$T/norb WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --rollback 2>&1 | grep -q 'no backup from before an update'"
check "2.34.0: --check-config reports a config error with exit 1 and a good config with exit 0" "WM_TEST_CHECKCONFIG=fail inst $HR --check-config | grep -q 'config error'; ! WM_TEST_CHECKCONFIG=fail WM_HOME=$HR WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --check-config >/dev/null 2>&1 && WM_TEST_CHECKCONFIG=ok WM_HOME=$HR WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --check-config >/dev/null 2>&1"
check "2.34.0: an update checks the new config with Klipper batch mode before the restart: an error is a warning that names the error, a good config is reported" "O=\$(WM_TEST_CHECKCONFIG=fail inst $HR --update); echo \"\$O\" | grep -q 'Klipper will probably NOT accept the new config' && echo \"\$O\" | grep -q 'must be specified'; O=\$(WM_TEST_CHECKCONFIG=ok inst $HR --update); echo \"\$O\" | grep -q 'Klipper loads the new config without an error'"
check "2.34.0: the batch-mode config check (devbox.py check) tells a good config from a broken one and leaves the config alone" "python3 -I -W ignore $ROOT/tests/test_devbox.py 2>&1 | tail -1 | grep -qi 'ok\|0 failed'"
check "2.34.0: an update where Klipper does not come back puts your settings back by itself, says so, and keeps a safety copy" "N0=\$(ls $HR/ultra-backup/settings/ 2>/dev/null | wc -l); O=\$(WM_TEST_KLIPPY_AFTER=error inst $HR --update); echo \"\$O\" | grep -q 'going back to your settings from before the update' && echo \"\$O\" | grep -q 'Klipper is ready again with your settings from before the update' && echo \"\$O\" | grep -q 'your settings were put back' && [ \$(ls $HR/ultra-backup/settings/ | wc -l) -gt \$N0 ]"
check "2.34.0: with --no-auto-rollback nothing is put back and the update says what to do by hand" "O=\$(WM_TEST_KLIPPY_AFTER=error inst $HR --update --no-auto-rollback); ! echo \"\$O\" | grep -q 'going back to your settings' && echo \"\$O\" | grep -q 'no-auto-rollback was given'"
check "2.34.0: an update where Klipper comes back does not roll back" "O=\$(inst $HR --update); ! echo \"\$O\" | grep -q 'going back to your settings' && echo \"\$O\" | grep -q 'Update finished'"
check "2.34.0: an update where Klipper was not ready before does not roll back (a problem that was already there)" "O=\$(WM_TEST_KLIPPY=error WM_TEST_KLIPPY_AFTER=error inst $HR --update); ! echo \"\$O\" | grep -q 'going back to your settings'"
check "2.25.0 (F-222): an update checks your own values and says they are untouched" "inst $HR --update | grep -q 'Your settings: untouched'"
check "2.25.0 (F-222): wm_protect.py puts back a changed saved variable, rotation_distance and SAVE_CONFIG block, and leaves new values alone" "python3 -I $ROOT/tests/test_protect.py 2>&1 | tail -1 | grep -q '^0 failed'"

sec "== repair, update, undo"
rm -f "$G2/.sudo.log"
inst "$G2" --repair >/dev/null
check "repair reinstalls service, nginx and can0 files" "grep -q 'moonraker.service' $G2/.sudo.log && grep -q 'nginx' $G2/.sudo.log && grep -q '99-wm-can0.rules' $G2/.sudo.log"
check "repair does not touch klipper state" "! grep -Eq 'systemctl (disable|stop) klipper' $G2/.sudo.log"
sed -i 's/^VERSION=.*/VERSION=0.0.1/' "$G2/wm-rpi-backup/install.conf"
echo "mine" > "$G2/printer_data/config/mine.cfg"
inst "$G2" --update > "$T/up.out"
check "update keeps user config" "[ -f $G2/printer_data/config/mine.cfg ]"
check "update shows what changed" "grep -q 'What changed since 0.0.1' $T/up.out"
check "update records the new version" "grep -q \"^VERSION=$(cat $ROOT/VERSION)\" $G2/wm-rpi-backup/install.conf"
check "update without earlier install fails" "! inst $T/empty --update"
UH="$T/uh"; mkdir -p "$UH"; inst "$UH" --from-stage "$T/stage" >/dev/null; echo mine > "$UH/printer_data/config/mine.cfg"
inst "$UH" --from-stage "$T/stage" >/dev/null
check "second install moved mine.cfg away" "[ ! -f $UH/printer_data/config/mine.cfg ]"
OLDD="$(ls -d $UH/wm-rpi-backup/old-* | sort | tail -1)"; mkdir -p "$OLDD/fluidd" "$UH/wm-rpi-backup/fluidd-${OLDD##*/old-}"
echo old > "$OLDD/fluidd/mark"; echo backup > "$UH/wm-rpi-backup/fluidd-${OLDD##*/old-}/mark"
printf 'y\ny\n' | WM_HOME="$UH" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --undo >/dev/null 2>&1
check "undo puts the moved-aside fluidd back and does not overwrite it with the Fluidd backup" "[ \"\$(cat $UH/fluidd/mark)\" = old ]"
check "undo puts mine.cfg back" "[ -f $UH/printer_data/config/mine.cfg ]"
check "undo keeps what it replaced" "ls -d $UH/wm-rpi-backup/undone-*"

sec "== doctor and support bundle"
check "doctor passes on a good install" "WM_TEST_SCREEN=1024x600 WM_TEST_TOUCH=1 WM_TEST_CANQUERY=$T/can_ok.txt WM_HOME=$G2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --doctor"
D='WM_HOME='"$G2"' WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash '"$ROOT"'/installer.sh --doctor'
check "doctor: calibration macros are ok on a good install" "eval \"$D\" 2>&1 | grep -q 'calibration macros rpi_calibration.cfg (included in printer.cfg, same as rpi-cfg)'"
rm -f "$G2/printer_data/config/rpi_calibration.cfg"
check "doctor reports a missing rpi_calibration.cfg" "eval \"$D\" 2>&1 | grep -q 'calibration macros file rpi_calibration.cfg is missing'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --doctor --fix-all >/dev/null 2>&1 </dev/null
check "Fix everything puts rpi_calibration.cfg back" "cmp $ROOT/rpi-cfg/rpi_calibration.cfg $G2/printer_data/config/rpi_calibration.cfg"
check "doctor names the base file by what it does: rpi_base.cfg ok as the base helpers, homing and bed warp wait file" "eval \"$D\" 2>&1 | grep -q 'base helpers, homing and bed warp wait rpi_base.cfg (included in printer.cfg, same as rpi-cfg)'"
mv "$G2/printer_data/config/rpi_base.cfg" "$T/rpi_base.saved"
check "doctor: a missing rpi_base.cfg says what breaks (no bed drop, homing, idle timeout)" "eval \"$D\" > $T/doc_homing.txt 2>&1; grep -q 'file rpi_base.cfg is missing' $T/doc_homing.txt && grep -q 'the bed drop (z_rise)' $T/doc_homing.txt"
mv "$T/rpi_base.saved" "$G2/printer_data/config/rpi_base.cfg"
check "rpicfg_role: every file in rpi-cfg has its own name and effect text" "(source <(sed -n '/^rpicfg_role() {/,/^}/p' $ROOT/installer.sh); for f in $ROOT/rpi-cfg/*.cfg; do b=\$(basename \$f); [ \"\$(rpicfg_role \$b name)\" != 'Pi config' ] && [ \"\$(rpicfg_role \$b effect)\" != 'the macros in it do not exist' ] || exit 1; done)"
sed -i '/include rpi_calibration.cfg/d' "$G2/printer_data/config/printer.cfg"
check "doctor reports a missing include line" "eval \"$D\" 2>&1 | grep -q 'printer.cfg does not include rpi_calibration.cfg'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --doctor --fix-all >/dev/null 2>&1 </dev/null
check "Fix everything adds the include line back (once)" "[ \$(grep -c 'include rpi_calibration.cfg' $G2/printer_data/config/printer.cfg) = 1 ]"
echo '# my edit' >> "$G2/printer_data/config/rpi_calibration.cfg"
check "doctor notices an edited rpi_calibration.cfg" "eval \"$D\" 2>&1 | grep -q 'rpi_calibration.cfg differs from the one in rpi-cfg'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --doctor --fix-all >/dev/null 2>&1 </dev/null
check "the fix is a 3-way merge: your edit stays in the file, the rest is the repository file" "grep -q '^# my edit\$' $G2/printer_data/config/rpi_calibration.cfg && grep -v '^# my edit\$' $G2/printer_data/config/rpi_calibration.cfg | cmp - $ROOT/rpi-cfg/rpi_calibration.cfg"
NB1=$(ls "$G2/printer_data/config" | grep -c "rpi_calibration.cfg.wm-before")
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg > "$T/rc.out" 2>&1 </dev/null
check "--rpi-cfg runs, is idempotent, adds no second include" "grep -q 'rpi_calibration.cfg is installed (printer.cfg already includes it)' $T/rc.out && [ \$(grep -c 'include rpi_calibration.cfg' $G2/printer_data/config/printer.cfg) = 1 ]"
check "--rpi-cfg with nothing changed makes no extra copy of rpi_calibration.cfg" "[ \$(ls $G2/printer_data/config/ | grep -c 'rpi_calibration.cfg.wm-before') = $NB1 ]"
check "--rpi-cfg dry run changes nothing" "rm -f $G2/printer_data/config/rpi_calibration.cfg; WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --rpi-cfg --dry-run >/dev/null 2>&1 </dev/null; [ ! -f $G2/printer_data/config/rpi_calibration.cfg ]"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg >/dev/null 2>&1 </dev/null
check "--rpi-cfg restores a deleted file" "cmp $ROOT/rpi-cfg/rpi_calibration.cfg $G2/printer_data/config/rpi_calibration.cfg"
check "nozzle: rpi_nozzle.cfg is installed and included, with its helper script" "cmp $ROOT/rpi-cfg/rpi_nozzle.cfg $G2/printer_data/config/rpi_nozzle.cfg && [ \$(grep -c '^\\[include rpi_nozzle.cfg\\]' $G2/printer_data/config/printer.cfg) = 1 ] && cmp $ROOT/scripts/wm_nozzle.py $G2/printer_data/wm-tools/wm_nozzle.py"
check "nozzle: the shell command extension is there too" "[ -f $G2/klipper/klippy/extras/gcode_shell_command.py ]"
check "nozzle: doctor is happy with the helper script" "eval \"$D\" 2>&1 | grep -q 'wm_nozzle.py (the helper behind _WM_NOZZLE_TYPE) is in place'"
# Rename wm_ -> rpi_ (2.6.0): a Pi with the old file names is renamed once, include lines follow, copies are kept
CF="$G2/printer_data/config"
mv "$CF/rpi_calibration.cfg" "$CF/wm_calibration.cfg"; mv "$CF/rpi_nozzle.cfg" "$CF/wm_nozzle.cfg"
echo '# my fan guard' > "$CF/wm_fan_guard.cfg"; echo '{"url": "http://x"}' > "$CF/wm_chamber_light.json"
sed -i 's/\[include rpi_calibration.cfg\]/[include wm_calibration.cfg]/; s/\[include rpi_nozzle.cfg\]/[include wm_nozzle.cfg]/' "$CF/printer.cfg"
printf '[include wm_fan_guard.cfg]\n' >> "$CF/extra_include_test.cfg"
echo '# my edit of the old name' >> "$CF/wm_calibration.cfg"
cp "$CF/printer.cfg" "$T/printer_before_rename.cfg"
check "doctor reports the old wm_ names" "eval \"$D\" 2>&1 | grep -q 'still have the old wm_ names'"
check "dry run renames nothing" "WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --rpi-cfg --dry-run >/dev/null 2>&1 </dev/null; [ -f $CF/wm_calibration.cfg ] && [ ! -e $CF/rpi_calibration.cfg ]"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg > "$T/ren.out" 2>&1 </dev/null
check "rename: the old files are gone, the rpi_ files exist" "[ ! -e $CF/wm_calibration.cfg ] && [ ! -e $CF/wm_nozzle.cfg ] && [ ! -e $CF/wm_fan_guard.cfg ] && [ ! -e $CF/wm_chamber_light.json ] && [ -f $CF/rpi_fan_guard.cfg ] && [ -f $CF/rpi_chamber_light.json ] && [ -f $CF/rpi_calibration.cfg ] && [ -f $CF/rpi_nozzle.cfg ]"
check "rename: printer.cfg includes the new names, each once, none of the old" "[ \$(grep -c 'include rpi_calibration.cfg' $CF/printer.cfg) = 1 ] && [ \$(grep -c 'include rpi_nozzle.cfg' $CF/printer.cfg) = 1 ] && ! grep -qE 'include wm_(calibration|nozzle)' $CF/printer.cfg"
check "rename: another config file's include line follows too" "grep -q '^\[include rpi_fan_guard.cfg\]' $CF/extra_include_test.cfg"
check "rename: the content of the files is kept (3-way merge: the edit made under the old name stays)" "grep -q 'my edit of the old name' $CF/rpi_calibration.cfg"
check "rename: old and new both present: the new one is kept and the old one is saved" "! grep -q 'my fan guard' $CF/rpi_fan_guard.cfg && grep -q 'my fan guard' $G2/ultra-backup/config/*/rename-*/wm_fan_guard.cfg"
check "rename: copies of the old files and printer.cfg are in ~/ultra-backup/config/<date>/rename-*" "ls $G2/ultra-backup/config/*/rename-*/wm_fan_guard.cfg $G2/ultra-backup/config/*/rename-*/printer.cfg >/dev/null"
check "rename: the SAVE_CONFIG block of printer.cfg is untouched" "[ \"\$(sed -n '/SAVE_CONFIG/,\$p' $CF/printer.cfg)\" = \"\$(sed -n '/SAVE_CONFIG/,\$p' $T/printer_before_rename.cfg)\" ]"
check "rename: doctor is clean of the old-name problem" "! eval \"$D\" 2>&1 | grep -q 'still have the old wm_ names'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg > "$T/ren2.out" 2>&1 </dev/null
check "rename: running it again renames nothing" "! grep -q 'renamed from wm_ to rpi_' $T/ren2.out"
rm -f "$G2/printer_data/wm-tools/wm_nozzle.py"
check "nozzle: doctor notices a missing helper script" "yes n | WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'wm_nozzle.py is missing or different'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg >/dev/null 2>&1 </dev/null
check "nozzle: --rpi-cfg puts the helper script back" "cmp $ROOT/scripts/wm_nozzle.py $G2/printer_data/wm-tools/wm_nozzle.py"
check "match: the helper script wm_canids.py is installed next to wm_nozzle.py" "cmp $ROOT/scripts/wm_canids.py $G2/printer_data/wm-tools/wm_canids.py && [ -x $G2/printer_data/wm-tools/wm_canids.py ]"
check "2.24.0 (F-221): E-step calibration: the helper wm_estep.py is installed next to wm_nozzle.py and executable" "cmp $ROOT/scripts/wm_estep.py $G2/printer_data/wm-tools/wm_estep.py && [ -x $G2/printer_data/wm-tools/wm_estep.py ]"
check "2.24.0 (F-221): E-step calibration: every macro block compiles and renders (jinja2), config read the way Klipper reads it" "o=\$(python3 -I $ROOT/tests/estep_render.py 2>&1); echo \"\$o\" | grep -q 'compiled [0-9]* macro blocks, 0 errors' && ! echo \"\$o\" | grep -q 'FAIL render'"
check "2.24.0 (F-221): E-step calibration: the helper writes and refuses correctly (offline test)" "python3 -I $ROOT/tests/test_wm_estep.py 2>&1 | tail -1 | grep -q '^0 failed'"
check "2.24.0 (F-221): E-step calibration: macros are in rpi_nozzle.cfg only, the button is in the Tool offsets group, the four pictures exist, the watcher counts it as busy, one picture shows big" "[ \$(grep -c '^\\[gcode_macro WM_ESTEP_CAL\\]' $ROOT/rpi-cfg/rpi_nozzle.cfg) = 1 ] && ! grep -q 'WM_ESTEP_CAL\\]' $ROOT/rpi-cfg/rpi_calibration.cfg && grep -q '\"E-step calibration\", \"WM_ESTEP_CAL\"' $ROOT/zr_tools/zr_tools.py && for n in prepare ruler zero measure; do [ -s $ROOT/zr_tools/wm_images/estep-\$n.png ] || exit 1; done && grep -q 'or estep' $ROOT/rpi-cfg/rpi_base.cfg && grep -q 'self.screen.height \* 0.60' $ROOT/zr_tools/ks_wm_patches.json"
check "2.25.1: no Jinja comment {# #} in any rpi-cfg file (Klipper cuts a config line at the first # and the macro fails to load)" "! grep -n '{#' $ROOT/rpi-cfg/*.cfg"
check "match: doctor is happy with wm_canids.py" "eval \"$D\" 2>&1 | grep -q 'wm_canids.py (the helper behind WM_EXTRUDER_SETUP) is in place'"
rm -f "$G2/printer_data/wm-tools/wm_canids.py"
check "match: doctor notices a missing wm_canids.py" "yes n | WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'wm_canids.py is missing or different'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg >/dev/null 2>&1 </dev/null
check "match: --rpi-cfg puts wm_canids.py back" "cmp $ROOT/scripts/wm_canids.py $G2/printer_data/wm-tools/wm_canids.py"

sec "== 2.8.0: Z offset tools, unload menu, safety check, virtual pins, chamber light, macro patches"
CF2="$G2/printer_data/config"
sed -i '/^# my edit/d' "$CF2/rpi_calibration.cfg"   # the two test edits above stay in the file now (3-way merge); take them out before the next checks compare with the repository file
check "rpi-cfg 2.10.0: rpi_base.cfg and rpi_calibration.cfg are installed and included once, the old separate files are not" "(for f in rpi_base.cfg rpi_calibration.cfg; do cmp $ROOT/rpi-cfg/\$f $CF2/\$f && [ \$(grep -c \"^\\[include \$f\\]\" $CF2/printer.cfg) = 1 ] || exit 1; done) && ! grep -qE 'include rpi_(homing|bed_soak|zoffset|virtual_pins|unload|safety|tool_leds|print_end|head_sensors|mcu|mcu_temps|light)\.cfg' $CF2/printer.cfg"
check "rpi-cfg 2.10.0: rpi_base.cfg is included above rpi_calibration.cfg (Klipper must read [wm_virtual_pins] first)" "[ \$(grep -n '^\\[include rpi_base.cfg\\]' $CF2/printer.cfg | cut -d: -f1) -lt \$(grep -n '^\\[include rpi_calibration.cfg\\]' $CF2/printer.cfg | cut -d: -f1) ]"
check "rpi-cfg 2.8.0: the new includes sit before the SAVE_CONFIG block" "! sed -n '/SAVE_CONFIG/,\$p' $CF2/printer.cfg | grep -qE 'include rpi_(base|calibration|homing|pi)'"
check "virtual pins: the driver is in both factory folders, in their checksum lists, and in the installed Klipper" "(for m in ultra ultra-s; do grep -q 'klipper/klippy/extras/wm_virtual_pins.py' $ROOT/factory/\$m/SHA256SUMS && [ -f $ROOT/factory/\$m/klipper/klippy/extras/wm_virtual_pins.py ] || exit 1; done; [ ! -d $G2/klipper/klippy/extras ] || cmp $ROOT/factory/ultra-s/klipper/klippy/extras/wm_virtual_pins.py $G2/klipper/klippy/extras/wm_virtual_pins.py)"
check "virtual pins: rpi_calibration.cfg uses a wm_pin and rpi_base.cfg defines the section first" "grep -q '^pin: wm_pin:nozzle_heat_growth' $ROOT/rpi-cfg/rpi_calibration.cfg && [ \$(grep -n '^\\[' $ROOT/rpi-cfg/rpi_base.cfg | head -1 | grep -c 'wm_virtual_pins') = 1 ]"
check "first run calibration: the old name is gone from the macros, the screen panel and the docs of rpi-cfg" "! grep -rn 'WM_FULL_CALIBRATION' $ROOT/rpi-cfg/*.cfg $ROOT/zr_tools/*.py $ROOT/installer.sh"
check "unload menu: the work macro is hidden, the menu and stop are not" "grep -q '^\\[gcode_macro _WM_UNLOAD_GO\\]' $ROOT/rpi-cfg/rpi_base.cfg && grep -q '^\\[gcode_macro WM_UNLOAD_MENU\\]' $ROOT/rpi-cfg/rpi_base.cfg && grep -q '^\\[gcode_macro _WM_UNLOAD_STOP\\]' $ROOT/rpi-cfg/rpi_base.cfg && ! grep -q '^\\[gcode_macro WM_UNLOAD_GO\\]' $ROOT/rpi-cfg/rpi_base.cfg"
check "factory macros (both models): trims and heat growth in _OFFSET_SET, pause guard, second wipe, light at print start, runout only while printing, TEST_W4 gone" "(for m in ultra ultra-s; do d=$ROOT/factory/\$m/config; grep -q 'wm_z_trim_t%d' \$d/change_macros.cfg && ! grep -q 'wm_z_trim_all' \$d/change_macros.cfg && grep -q 'wm_nozzle_growth' \$d/change_macros.cfg && grep -q '^\\[gcode_macro _WM_PAUSE_STATE\\]' \$d/macros.cfg && grep -q 'Nothing to resume' \$d/macros.cfg && grep -q 'WIPE_NOZZLE  .*right before the mesh' \$d/macros.cfg && grep -q 'WM_CHAMBER_LIGHT STATE=on' \$d/macros.cfg && ! grep -q 'TEST_W4' \$d/offset_calibrate.cfg && for n in 0 1 2 3; do grep -q 'print_stats.state == \"printing\"' \$d/extruder\$n.cfg || exit 1; done || exit 1; done)"
check "macro patches: the list is up to date with the factory files of this version" "[ ! -d $ROOT/.git ] || python3 $ROOT/tools/make_macro_patches.py e98e653 2.33.0 --check"
check "2.13.0: hub.cfg (both models): tangle messages, the pause stays, each sensor calls _WM_ENDLESS_TANGLE only when it exists" "(for m in ultra ultra-s; do f=$ROOT/factory/\$m/config/hub.cfg; [ \$(grep -c 'Filament tangle on T' \$f) = 4 ] && [ \$(grep -c '^pause_on_runout: True' \$f) = 4 ] && [ \$(grep -c '_WM_ENDLESS_TANGLE T=' \$f) = 4 ] && [ \$(grep -c 'gcode_macro _WM_ENDLESS_TANGLE\" in printer' \$f) = 4 ] && ! grep -q 'Filament runout on path' \$f || exit 1; done)"
check "2.13.0: heat at the wipe position: the two macros in rpi_base.cfg, M109 and _WAIT_TOOL_TEMPERATURE call them around the wait only when they exist (both models)" "grep -q '^\\[gcode_macro _WM_HEAT_AT_WIPE\\]' $ROOT/rpi-cfg/rpi_base.cfg && grep -q '^\\[gcode_macro _WM_HEAT_BACK\\]' $ROOT/rpi-cfg/rpi_base.cfg && (for m in ultra ultra-s; do for f in macros.cfg change_macros.cfg; do g=$ROOT/factory/\$m/config/\$f; [ \$(grep -c '_WM_HEAT_AT_WIPE T=' \$g) = 1 ] && [ \$(grep -c '^ *_WM_HEAT_BACK\$' \$g) = 1 ] && [ \$(grep -c 'gcode_macro _WM_HEAT_AT_WIPE\\\" in printer' \$g) = 1 ] || exit 1; done; done)"
check "2.13.0: heat at the wipe position renders: trip only in a print, for the tool on the carriage, when it is cold; back to the old spot; a left-over flag is cleared" "python3 -I $ROOT/tests/heat_wipe_render.py $ROOT/rpi-cfg/rpi_base.cfg"
check "2.14.0: tool setter position helper renders: start with the sensed lowering, one Find button, quick search, wide search only after its window, block middles, both saves, Restore old" "python3 -I $ROOT/tests/setter_render.py $ROOT/rpi-cfg/rpi_calibration.cfg"
check "2.14.0: wm_tool_touch (TOOL_CALIBRATE_TOUCH): result per NAME, travel limit, low acceleration put back, false touches repeated, OPTIONAL misses are no error" "python3 -I $ROOT/tests/tool_touch_test.py $ROOT/factory/ultra-s/klipper/klippy/extras/wm_tool_touch.py"
check "2.14.0: wm_tool_touch is in both factory folders and their checksum lists, the same file, and the update copies it before rpi_calibration.cfg" "cmp $ROOT/factory/ultra/klipper/klippy/extras/wm_tool_touch.py $ROOT/factory/ultra-s/klipper/klippy/extras/wm_tool_touch.py && (for m in ultra ultra-s; do grep -q 'klipper/klippy/extras/wm_tool_touch.py' $ROOT/factory/\$m/SHA256SUMS || exit 1; done) && grep -q 'cp \"\$tt\" \"\$ex/wm_tool_touch.py\"' $ROOT/installer.sh && grep -q 'rpi_calibration.cfg \] && \[ -d \"\$ex\" \] && \[ ! -f \"\$ex/wm_tool_touch.py\" \]' $ROOT/installer.sh && grep -q '^\[wm_tool_touch\]' $ROOT/rpi-cfg/rpi_calibration.cfg && [ \$(grep -c 'tools_calibrate.touch' $ROOT/rpi-cfg/rpi_calibration.cfg) = 0 ] && cmp $ROOT/factory/ultra/klipper/klippy/extras/tools_calibrate_core.py $ROOT/factory/ultra-s/klipper/klippy/extras/tools_calibrate_core.py && ! grep -q TOOL_CALIBRATE_TOUCH $ROOT/factory/ultra-s/klipper/klippy/extras/tools_calibrate_core.py"
check "factory offset calibration (both models): touches within 0.05 mm (CELL firmware V2, F-117), 6 tries" "(for m in ultra ultra-s; do grep -q '^samples_tolerance: 0.05 ' $ROOT/factory/\$m/config/offset_calibrate.cfg && grep -q '^samples_tolerance_retries: 6 ' $ROOT/factory/\$m/config/offset_calibrate.cfg || exit 1; done)"
mkdir -p "$T/ksp"; printf 'import logging\nclass Prompt:\n    def decode(self, data):\n        if data.startswith("prompt_text"):\n            self.text = data\n            return\n        elif data.startswith("prompt_button "):\n            pass\n\n    def set_button(self, name, gcode, style="default"):\n        if self.groups:\n            pass\n        else:\n            self.scroll_box.add(button)\n\n    def set_footer_button(self, name, gcode, style="default"):\n        pass\n' > "$T/ksp/prompts.py"
check "2.14.0: pictures in a touchscreen window: the two prompts changes apply once to KlipperScreen's lines, the file compiles, a second run changes nothing; the pictures and the copy step are there" "python3 - <<PYEOF
import json, sys
d = [h for h in json.load(open('$ROOT/zr_tools/ks_wm_patches.json'))['prompts'] if 'old' in h and ('prompt_image' in h['new'] or 'def add_images' in h['new'])]; assert len(d) == 2
p = '$T/ksp/prompts.py'; s = open(p).read()
for h in d:
    assert s.count(h['old']) == 1, h['old'][:40]
    s = s.replace(h['old'], h['new'])
for h in d:
    assert s.count(h['old']) == 0 and h['new'] in s
compile(s, p, 'exec')
assert 'def add_images' in s and 'startswith(\"prompt_image\")' in s and 'wm_images' in s
PYEOF
[ \$? = 0 ] && for n in setter-height setter-place setter-compare; do [ -s $ROOT/zr_tools/wm_images/\$n.png ] || exit 1; done && grep -q 'cp \"\$d\"/wm_images/\*.png \"\$KS_DIR/wm_images/\"' $ROOT/scripts/screen_board.sh && grep -q '\"Tool setter position\", \"WM_SETTER_PROBE_POSITION\"' $ROOT/zr_tools/zr_tools.py && [ \$(grep -c 'prompt_image setter-height setter-place setter-compare' $ROOT/rpi-cfg/rpi_calibration.cfg) = 3 ]"
check "2.15.0: touchscreen pages for the tool setter steps and the Z trim: the prompts changes open the page in place of the window, values go to the page, a page that cannot load leaves the window; both pages are copied" "python3 -I $ROOT/tests/ks_pages_test.py $ROOT 2>/dev/null"
check "2.26.0: KlipperScreen patch check: patch_ks_wm.py --check says present, missing or different and changes nothing; the screen board doctor uses it for every file the update patches" "python3 -I $ROOT/tests/test_ks_patch_check.py | tail -1 | grep -q '^0 failed' && grep -q 'patch_ks_wm.py\" --check' $ROOT/scripts/screen_board.sh && [ \$(grep -c 'KS_WM_KEYS' $ROOT/scripts/screen_board.sh) -ge 3 ]"
check "2.13.0: KlipperScreen patch list: screen.py gets the retry-by-itself change, and no change can apply twice" "python3 -c \"import json; d=json.load(open('$ROOT/zr_tools/ks_wm_patches.json')); s=d['screen']; assert any('_wm_retry_later' in h['new'] for h in s if 'new' in h); assert all(h['old'] not in h['new'] for k in d for h in d[k] if 'old' in h)\""
check "2.23.0 (F-208): KlipperScreen patch list: gcodes.py and job_status.py open the Choose toolheads page first, the screen board script patches gcodes.py, a second run changes nothing" "python3 -c \"import json,os,subprocess,sys,tempfile; d=json.load(open('$ROOT/zr_tools/ks_wm_patches.json')); g=[h for h in d['gcodes'] if 'old' in h]; assert len(g)==1 and 'zr_pending_print' in g[0]['new'] and 'zr_pending_print' in d['job_status'][-1]['new']; t=tempfile.mkdtemp(); p=os.path.join(t,'gcodes.py'); open(p,'w').write('# a\\n'+g[0]['old']); r=[subprocess.run([sys.executable,'-I','$ROOT/zr_tools/patch_ks_wm.py','gcodes',p]).returncode for i in range(2)]; assert r==[10,0] and 'zr_pending_print' in open(p).read()\" && grep -q 'gcodes:panels/gcodes.py' $ROOT/scripts/screen_board.sh"
check "2.23.2 (F-220, F-212): KlipperScreen patch list: prompts2 gives every popup the Large bold writing and the Nozzle clean colours, the Fine Tuning zero button calls _WM_LIVE_Z_ZERO, a board with the old name is renamed, a second run changes nothing" "python3 -I -W ignore $ROOT/tests/test_f220.py"
check "2.12.0: PRINT_END and CANCEL_PRINT also reset the saved tool mapping copies, RESUME purges 20 mm (both models)" "(for m in ultra ultra-s; do f=$ROOT/factory/\$m/config/macros.cfg; [ \$(grep -c 'SAVE_VARIABLE VARIABLE=box_modify_t{i}_backup VALUE={i}' \$f) = 2 ] && awk '/^\\[gcode_macro PRINT_END\\]/{p=1} /^\\[gcode_macro E_axis_move\\]/{p=0} p&&/_backup VALUE=\\{i\\}/{ok=1} END{exit !ok}' \$f && awk '/^\\[gcode_macro CANCEL_PRINT\\]/{p=1} p&&/_backup VALUE=\\{i\\}/{ok=1} END{exit !ok}' \$f && grep -q '^    E_axis_move L={pl} S=300' \$f && grep -q 'else 20 %}' \$f && ! grep -q '^    E_axis_move L=10 S=300' \$f || exit 1; done)"
MP="$T/mp"; rm -rf "$MP"; mkdir -p "$MP"; if [ -d "$ROOT/.git" ]; then for f in macros.cfg change_macros.cfg offset_calibrate.cfg extruder0.cfg extruder1.cfg extruder2.cfg extruder3.cfg; do git -C "$ROOT" show 8b47b12:factory/ultra-s/config/$f > "$MP/$f"; done
check "macro patches: without --write nothing changes and the exit code says changes are needed" "cp -r $MP $MP.0; python3 -I $ROOT/scripts/wm_macro_patches.py $MP >/dev/null; [ \$? = 10 ] && diff -r $MP $MP.0"
python3 -I "$ROOT/scripts/wm_macro_patches.py" "$MP" --write --stamp TST >/dev/null
check "macro patches: the 2.7.10 files become the files of this version (2.8.0 and 2.9.0 fixes), with a copy of each changed file" "(for f in macros.cfg change_macros.cfg offset_calibrate.cfg extruder0.cfg extruder1.cfg extruder2.cfg extruder3.cfg; do cmp $MP/\$f $ROOT/factory/ultra-s/config/\$f && [ -f $MP/\$f.wm-before-macro-patches-TST ] || exit 1; done)"
check "macro patches: a second run changes nothing" "python3 -I $ROOT/scripts/wm_macro_patches.py $MP --write --stamp TS2; [ \$? = 0 ] && ! ls $MP/*.wm-before-macro-patches-TS2 2>/dev/null"
git -C "$ROOT" show 8b47b12:factory/ultra-s/config/change_macros.cfg | sed 's/Z={offset_z} move=1/Z={offset_z + 0.01} move=1/' > "$MP/change_macros.cfg"
check "macro patches: lines you changed yourself are left alone and reported (exit 11)" "python3 -I $ROOT/scripts/wm_macro_patches.py $MP --write --stamp TS3 > $T/mp.out; [ \$? = 11 ] && grep -q 'not changed change_macros.cfg' $T/mp.out && grep -q 'offset_z + 0.01' $MP/change_macros.cfg"
fi
check "file merge: the update runs step_macro_files after the printer.cfg merge, and step_rpicfg merges each rpi file with filemerge_one" "grep -q 'step_cfgmerge; step_macro_files;' $ROOT/installer.sh && grep -q 'filemerge_one \"\$cd/\$f\" \"\$SCRIPT_DIR/rpi-cfg/\$f\"' $ROOT/installer.sh"
check "file merge: scripts/wm_filemerge.py tests pass (the five cases, first update without a baseline, nothing changes without --write)" "python3 -I -W ignore $ROOT/tests/test_filemerge.py"
check "file merge: filemerge_one in the installer keeps a line you changed, brings in a line WonderMaker changed, records the baseline in wm-baseline, and a dry run of the step changes nothing" "FM=\$(mktemp -d); mkdir -p \$FM/home \$FM/new; printf 'a\\nb\\nc\\nd\\ne\\nf\\ng\\nh\\n' > \$FM/home/m.cfg; cp \$FM/home/m.cfg \$FM/new/m.cfg; mkdir -p \$FM/home/printer_data/wm-baseline; cp \$FM/home/m.cfg \$FM/home/printer_data/wm-baseline/m.cfg; sed -i 's/^b\$/b MINE/' \$FM/home/m.cfg; sed -i 's/^g\$/g NEW/' \$FM/new/m.cfg; (HOME_DIR=\$FM/home; SCRIPT_DIR=$ROOT; STAMP=T; warn_later() { :; }; source <(sed -n '/^cfgmerge_base_dir() /p;/^filemerge_py() /p;/^filemerge_one() {/,/^}/p' $ROOT/installer.sh); filemerge_one \$FM/home/m.cfg \$FM/new/m.cfg x/m.cfg >/dev/null) && grep -q '^b MINE\$' \$FM/home/m.cfg && grep -q '^g NEW\$' \$FM/home/m.cfg && cmp \$FM/new/m.cfg \$FM/home/printer_data/wm-baseline/m.cfg && ls \$FM/home/backup/m.cfg.wm-before-merge-T >/dev/null"

sec "== 2.9.0: head sensors and load queue, speed test, faster homing and tool change, idle timeout, live Z, screen changes"
check "rpi-cfg 2.9.0: the head sensor queue (in rpi_base.cfg) and the speed test (now inside rpi_nozzle.cfg, 2.21.1) are installed and included once, before the SAVE_CONFIG block" "grep -q '^\\[delayed_gcode WM_HEAD_SENSOR_WATCH\\]' $CF2/rpi_base.cfg && cmp $ROOT/rpi-cfg/rpi_nozzle.cfg $CF2/rpi_nozzle.cfg && grep -q '^\\[auto_speed\\]' $CF2/rpi_nozzle.cfg && [ \$(grep -c '^\\[include rpi_nozzle.cfg\\]' $CF2/printer.cfg) = 1 ] && [ ! -e $CF2/rpi_auto_speed.cfg ] && ! grep -q 'include rpi_auto_speed' $CF2/printer.cfg && ! sed -n '/SAVE_CONFIG/,\$p' $CF2/printer.cfg | grep -qE 'include rpi_(base|nozzle)'"
check "speed test: the Save script is copied to wm-tools" "cmp $ROOT/scripts/wm_speed_limits.py $G2/printer_data/wm-tools/wm_speed_limits.py"
check "speed test: the module is in both factory folders and their checksum lists" "(for m in ultra ultra-s; do for f in auto_speed.py autospeed/__init__.py autospeed/funcs.py autospeed/main.py autospeed/move.py autospeed/wrappers.py autospeed/LICENSE; do grep -q \"klipper/klippy/extras/\$f\\$\" $ROOT/factory/\$m/SHA256SUMS && [ -f $ROOT/factory/\$m/klipper/klippy/extras/\$f ] || exit 1; done; done)"
check "speed test: the module keeps the last result and the input shaper limit (WonderMaker changes)" "grep -q '_wm_save_last' $ROOT/factory/ultra-s/klipper/klippy/extras/autospeed/main.py && grep -q 'shaper_at_test' $ROOT/factory/ultra-s/klipper/klippy/extras/autospeed/main.py && grep -q 'test_x_min' $ROOT/factory/ultra-s/klipper/klippy/extras/autospeed/main.py"
check "speed test: no test and no Save without a calibrated input shaper" "grep -q 'Input shaper first' $ROOT/rpi-cfg/rpi_nozzle.cfg && grep -q 'not started, the input shaper is not calibrated' $ROOT/rpi-cfg/rpi_nozzle.cfg && grep -q 'not saved, the input shaper is not calibrated' $ROOT/rpi-cfg/rpi_nozzle.cfg"
SL="$T/sl"; rm -rf "$SL"; mkdir -p "$SL/printer_data/config"; cp "$ROOT/factory/ultra-s/config/printer.cfg" "$SL/printer_data/config/printer.cfg"
check "speed test Save script: writes only max_accel and max_velocity of [printer], with a copy" "HOME=$SL python3 $ROOT/scripts/wm_speed_limits.py 4800 700 | grep -q 'saved max_accel 4800' && [ \$(diff $ROOT/factory/ultra-s/config/printer.cfg $SL/printer_data/config/printer.cfg | grep -c '^>') = 2 ] && grep -q '^max_accel: 4800' $SL/printer_data/config/printer.cfg && ls $SL/printer_data/config/printer.cfg.wm-before-autospeed-*"
check "speed test Save script: refuses values out of range and changes nothing" "cp $SL/printer_data/config/printer.cfg $SL/p0; HOME=$SL python3 $ROOT/scripts/wm_speed_limits.py 99999 700 | grep -q FAILED; cmp $SL/p0 $SL/printer_data/config/printer.cfg"
check "removing the shell command extension also takes the speed test (rpi_nozzle.cfg) out" "grep -q 'for own in rpi_nozzle.cfg rpi_timelapse.cfg; do' $ROOT/installer.sh"
check "factory extruder files (both models): the load mark for the head sensor queue, only when its macro exists" "(for m in ultra ultra-s; do for n in 0 1 2 3; do grep -q \"_WM_HEAD_MARK T=\$n\" $ROOT/factory/\$m/config/extruder\$n.cfg && grep -q 'gcode_macro _WM_HEAD_MARK\" in printer' $ROOT/factory/\$m/config/extruder\$n.cfg || exit 1; done; done)"
check "factory printer.cfg (both models, all variants): X/Y homing 80; rpi_base.cfg: z_rise skipped in a print, G28 X Z homes, idle timeout spares a paused print" "(for f in $ROOT/factory/*/config/printer.cfg $ROOT/factory/*/config-variants/printer?.cfg; do [ \$(grep -c '^homing_speed:80' \$f) = 2 ] || exit 1; done) && H=$ROOT/rpi-cfg/rpi_base.cfg && grep -q 'a print has its own Z clearance' \$H && grep -q 'set hz = params.Z is defined' \$H && grep -q 'Idle timeout during a pause' \$H"
check "factory macros (both models): live Z adjust per tool in _OFFSET_SET, one Z trim per tool, dead macros gone; START_PRINT has the guarded bed warp lines and ADAPTIVE as a number" "(for m in ultra ultra-s; do d=$ROOT/factory/\$m/config; grep -q '_WM_LIVEZ' \$d/change_macros.cfg && ! grep -q 'wm_z_trim_all' \$d/change_macros.cfg && ! grep -qE '_SAVE_SPEED|_RESTORE_SPEED|_OFFSET_RESET' \$d/change_macros.cfg && ! grep -qE '_START_PROBE|_RGB_CLOSE' \$d/macros.cfg && grep -q 'if \"gcode_macro _WM_BED_SOAK_MARK\" in printer' \$d/macros.cfg && grep -q 'if \"gcode_macro _WM_BED_SOAK\" in printer' \$d/macros.cfg && grep -q 'params.ADAPTIVE|int == 1' \$d/macros.cfg && ! grep -q _GANTRY_TRIGGER \$d/load_cell.cfg || exit 1; done)"
check "screen 2.9.0: the KlipperScreen changes are applied at install and update, and wm_sensors.py is copied" "[ \$(grep -c 'patch_ks_wm' $ROOT/scripts/screen_board.sh) -ge 3 ] && grep -q 'wm_sensors.py' $ROOT/scripts/screen_board.sh && python3 -c \"import json; d=json.load(open('$ROOT/zr_tools/ks_wm_patches.json')); assert set(d) == {'extrude', 'job_status', 'fine_tune', 'prompts', 'prompts2', 'screen', 'main_menu', 'temperature', 'gcodes'}\""
mkdir -p "$T/ksg"; printf 'class P:\n    def update_graph_visibility(self, force_hide=False):\n        if self.left_panel is None:\n            return\n' > "$T/ksg/main_menu.py"; printf 'class P:\n    def update_graph_visibility(self, force_hide=False):\n        count = 0\n' > "$T/ksg/temperature.py"
check "screen 2.11.0: no temperature graph on the main menu and the Temperature page (changed once, a second run changes nothing)" "python3 $ROOT/zr_tools/patch_ks_wm.py main_menu $T/ksg/main_menu.py; [ \$? = 10 ] && python3 $ROOT/zr_tools/patch_ks_wm.py temperature $T/ksg/temperature.py; [ \$? = 10 ] && [ \$(grep -c '^        force_hide = True' $T/ksg/main_menu.py $T/ksg/temperature.py | grep -c ':1') = 2 ] && python3 $ROOT/zr_tools/patch_ks_wm.py main_menu $T/ksg/main_menu.py && python3 $ROOT/zr_tools/patch_ks_wm.py temperature $T/ksg/temperature.py && grep -q 'main_menu:panels/main_menu.py temperature:panels/temperature.py' $ROOT/scripts/screen_board.sh"
check "screen 2.11.0: a KlipperScreen stop is a clean stop (start script traps SIGTERM, exit 0), ordered after the rescue window, old boards fixed at the update, every restart goes through ks_restart" "grep -q \"trap 'kill -TERM\" $ROOT/scripts/screen_board.sh && grep -q 'RESCUE_AFTER=\" wm-screen-rescue.service\"' $ROOT/scripts/screen_board.sh && grep -q '^    ks_stop_fix\$' $ROOT/scripts/screen_board.sh && grep -q 'SuccessExitStatus=1' $ROOT/scripts/screen_board.sh && [ \$(grep -c 'systemctl restart KlipperScreen' $ROOT/scripts/screen_board.sh) = 1 ]"
check "bed warp wait 2.11.0: the rules (cold bed, warm bed, switch off, unheated bed, measured and scaled waits) render right" "python3 -I $ROOT/tests/bed_soak_render.py | tail -1 | grep -q 'failed: 0'"
check "bed warp wait: rpi_base.cfg carries it (no separate rpi_bed_soak.cfg), installed and included once, above SAVE_CONFIG" "grep -q '_WM_BED_SOAK' $CF2/rpi_base.cfg && [ ! -e $CF2/rpi_bed_soak.cfg ] && [ \$(grep -c '^\\[include rpi_base.cfg\\]' $CF2/printer.cfg) = 1 ] && ! sed -n '/SAVE_CONFIG/,\$p' $CF2/printer.cfg | grep -q 'include rpi_base'"
check "print start purge (F-105): START_PRINT of both models calls _WM_START_PURGE only when it exists, rpi_base.cfg defines it, wm_print_info is loaded by printer.cfg and has its driver" "(for m in ultra ultra-s; do grep -q '_WM_START_PURGE INITIAL_TOOL={INITIAL_TOOL} EXTRUDER={EXTRUDER}' $ROOT/factory/\$m/config/macros.cfg && grep -q '^\\[wm_print_info\\]' $ROOT/factory/\$m/config/printer.cfg && [ -f $ROOT/factory/\$m/klipper/klippy/extras/wm_print_info.py ] && grep -q wm_print_info.py $ROOT/factory/\$m/SHA256SUMS || exit 1; done) && grep -q '^\\[gcode_macro _WM_START_PURGE\\]' $ROOT/rpi-cfg/rpi_base.cfg"
# F-103/F-105: an older install (2.15.0 and before) has rpi_homing.cfg and rpi_bed_soak.cfg as separate included files: the update moves them to ultra-backup, drops the include lines, and copies the wm_print_info driver
rm -rf "$T/hjoin"; cp -a "$G2" "$T/hjoin"
printf '[homing_override]\naxes: z\n' > "$T/hjoin/printer_data/config/rpi_homing.cfg"; printf '[gcode_macro _OLD_SOAK]\ngcode:\n    M118 x\n' > "$T/hjoin/printer_data/config/rpi_bed_soak.cfg"
sed -i '0,/^\[include rpi_base.cfg\]/s//[include rpi_homing.cfg]\n[include rpi_bed_soak.cfg]\n[include rpi_base.cfg]/' "$T/hjoin/printer_data/config/printer.cfg"
rm -f "$T/hjoin/klipper/klippy/extras/wm_print_info.py"
WM_HOME="$T/hjoin" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg > "$T/hjoin.out" 2>&1 </dev/null
HJ="$T/hjoin/printer_data/config"
check "join 2.16.0: old rpi_homing.cfg and rpi_bed_soak.cfg are moved to ultra-backup, their include lines are gone, rpi_base.cfg is included once" "[ ! -e $HJ/rpi_homing.cfg ] && [ ! -e $HJ/rpi_bed_soak.cfg ] && ls $T/hjoin/ultra-backup/config/*/rpi-join-*/rpi_homing.cfg $T/hjoin/ultra-backup/config/*/rpi-join-*/rpi_bed_soak.cfg >/dev/null && ! grep -qE 'include rpi_(homing|bed_soak)' $HJ/printer.cfg && [ \$(grep -c '^\\[include rpi_base.cfg\\]' $HJ/printer.cfg) = 1 ] && cmp $ROOT/rpi-cfg/rpi_base.cfg $HJ/rpi_base.cfg"
check "join 2.16.0: the wm_print_info driver is copied into Klipper's extras by the update" "cmp $ROOT/factory/ultra-s/klipper/klippy/extras/wm_print_info.py $T/hjoin/klipper/klippy/extras/wm_print_info.py || cmp $ROOT/factory/ultra/klipper/klippy/extras/wm_print_info.py $T/hjoin/klipper/klippy/extras/wm_print_info.py"
rm -rf "$T/hjoin"
# 2.21.1: rpi_auto_speed.cfg is part of rpi_nozzle.cfg now: an older install has it as a separate included file
rm -rf "$T/asjoin"; cp -a "$G2" "$T/asjoin"
printf '[gcode_macro WM_AUTO_SPEED]\ngcode:\n    M118 old\n' > "$T/asjoin/printer_data/config/rpi_auto_speed.cfg"
sed -i '0,/^\[include rpi_nozzle.cfg\]/s//[include rpi_nozzle.cfg]\n[include rpi_auto_speed.cfg]/' "$T/asjoin/printer_data/config/printer.cfg"
WM_HOME="$T/asjoin" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --rpi-cfg > "$T/asjoin.out" 2>&1 </dev/null
AJ="$T/asjoin/printer_data/config"
check "join 2.21.1: the old rpi_auto_speed.cfg is moved to ultra-backup, its include line is gone, the speed test comes from rpi_nozzle.cfg once" "[ ! -e $AJ/rpi_auto_speed.cfg ] && ls $T/asjoin/ultra-backup/config/*/rpi-join-*/rpi_auto_speed.cfg >/dev/null && ! grep -q 'include rpi_auto_speed' $AJ/printer.cfg && [ \$(grep -c '^\\[include rpi_nozzle.cfg\\]' $AJ/printer.cfg) = 1 ] && [ \$(grep -c '^\\[gcode_macro WM_AUTO_SPEED\\]' $AJ/rpi_nozzle.cfg) = 1 ] && cmp $ROOT/rpi-cfg/rpi_nozzle.cfg $AJ/rpi_nozzle.cfg"
rm -rf "$T/asjoin"
check "bed warp wait 2.11.0: an update brings the START_PRINT lines and ADAPTIVE fix into a 2.10.0 macros.cfg, and a second run changes nothing" "rm -rf $T/mp && mkdir -p $T/mp && ( cd $ROOT && git show 72d16a2:factory/ultra-s/config/macros.cfg ) > $T/mp/macros.cfg 2>/dev/null || cp $ROOT/factory/ultra-s/config/macros.cfg $T/mp/macros.cfg; python3 -I $ROOT/scripts/wm_macro_patches.py $T/mp --write --stamp t >/dev/null; cmp $T/mp/macros.cfg $ROOT/factory/ultra-s/config/macros.cfg && python3 -I $ROOT/scripts/wm_macro_patches.py $T/mp >/dev/null"
check "screen 2.11.0: the ZR Tools page has the calibration buttons and the Bed warp wait button" "grep -q 'WM_LIVE_Z_MENU' $ROOT/zr_tools/zr_tools.py && grep -q 'WM_OFFSETS_Z_HOT' $ROOT/zr_tools/zr_tools.py && grep -q 'Bed warp wait.*WM_BED_SOAK_MENU' $ROOT/zr_tools/zr_tools.py && grep -q 'wm_sensors' $ROOT/zr_tools/zr_views.py"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --light > "$T/li0.out" 2>&1 </dev/null
check "chamber light: without a screen board nothing is set up" "grep -q 'The screen board has not announced its chamber light yet' $T/li0.out && ! grep -q 'power chamber_light' $CF2/moonraker.conf && ! python3 $ROOT/scripts/wm_rpi_pi.py has $CF2 light"
echo '{"url": "http://10.0.0.9:8765"}' > "$CF2/rpi_chamber_light.json"
check "chamber light: dry run changes nothing" "WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --light --dry-run >/dev/null 2>&1 </dev/null; ! grep -q 'power chamber_light' $CF2/moonraker.conf && ! python3 $ROOT/scripts/wm_rpi_pi.py has $CF2 light"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --light > "$T/li1.out" 2>&1 </dev/null
check "chamber light: the power device is written for the board address, with a copy of moonraker.conf" "[ \$(grep -c 'http://10.0.0.9:8765/light' $CF2/moonraker.conf) = 3 ] && grep -q '^\\[power chamber_light\\]' $CF2/moonraker.conf && ls $CF2/moonraker.conf.wm-before-light-*"
check "chamber light: WM_CHAMBER_LIGHT is the part light of rpi_pi.cfg, included once, before the SAVE_CONFIG block" "python3 $ROOT/scripts/wm_rpi_pi.py has $CF2 light && grep -q '^\\[gcode_macro WM_CHAMBER_LIGHT\\]' $CF2/rpi_pi.cfg && [ \$(grep -c '^\\[include rpi_pi.cfg\\]' $CF2/printer.cfg) = 1 ] && [ ! -e $CF2/rpi_light.cfg ] && ! sed -n '/SAVE_CONFIG/,\$p' $CF2/printer.cfg | grep -q 'include rpi_pi'"
NL1=$(ls "$CF2" | grep -c 'wm-before-light')
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --light > "$T/li2.out" 2>&1 </dev/null
check "chamber light: a second run changes nothing and makes no copies" "grep -q 'already has the chamber light' $T/li2.out && [ \$(ls $CF2 | grep -c 'wm-before-light') = $NL1 ] && [ \$(grep -c '^\\[include rpi_pi.cfg\\]' $CF2/printer.cfg) = 1 ] && [ \$(grep -c '^\\[gcode_macro WM_CHAMBER_LIGHT\\]' $CF2/rpi_pi.cfg) = 1 ]"
check "chamber light F-155: when nothing changed Klipper is not restarted" "grep -q 'did not change, so Klipper was not restarted' $T/li2.out && ! grep -q 'Restarting Klipper' $T/li2.out"
cp -p "$CF2/rpi_pi.cfg" "$T/rpi_pi.keep"; rm -f "$CF2/rpi_pi.cfg"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 WM_TEST_BUSY="a macro or a print is running" bash "$ROOT/installer.sh" --light > "$T/li3.out" 2>&1 </dev/null
check "chamber light F-155: the macro is written but Klipper is NOT restarted while it is busy" "grep -q 'Klipper was NOT restarted because it is busy' $T/li3.out && ! grep -q 'Restarting Klipper' $T/li3.out && [ -f $CF2/rpi_pi.cfg ]"
rm -f "$CF2/rpi_pi.cfg"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --light > "$T/li4.out" 2>&1 </dev/null
check "chamber light F-155: when the macro changed and Klipper is idle it is restarted" "grep -q 'Restarting Klipper' $T/li4.out"
echo '{"url": "http://10.0.0.20:8765"}' > "$CF2/rpi_chamber_light.json"
check "chamber light: the doctor notices a new board address" "WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 </dev/null | grep -q 'chamber light: moonraker.conf has no \\[power chamber_light\\] for the screen board at http://10.0.0.20:8765'"
WM_HOME="$G2" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --light >/dev/null 2>&1 </dev/null
check "chamber light: a new board address is corrected" "[ \$(grep -c 'http://10.0.0.20:8765/light' $CF2/moonraker.conf) = 3 ] && ! grep -q '10.0.0.9' $CF2/moonraker.conf"
check "chamber light: --help lists --light, and the screen patches look for the Moonraker call" "bash $ROOT/installer.sh --help | grep -q -- '--light' && [ \$(grep -c 'machine.device_power.post_device' $ROOT/scripts/screen_board.sh) = 2 ]"
rm -f "$CF2/rpi_chamber_light.json"
CI="$T/ci"; mkdir -p "$CI"; for i in 0 1 2 3; do cp "$ROOT/factory/ultra-s/config/wm_zru_thr$i.cfg" "$CI/"; sed -i "s/^canbus_uuid:.*/canbus_uuid: ac000000000$((i+1))/" "$CI/wm_zru_thr$i.cfg"; done
rm -rf "$T/ci0"; cp -r "$CI" "$T/ci0"
check "canids script: show lists the four ids" "[ \$(python3 $ROOT/scripts/wm_canids.py --config $CI show | grep -c '^T[0-3] [0-9a-f]\\{12\\}\$') = 4 ]"
check "canids script: apply swaps two ids, keeps a copy of those two files only, touches nothing else" "( A=\$(python3 $ROOT/scripts/wm_canids.py --config $CI show | awk '{print \$2}' | tr '\\n' ' '); set -- \$A; python3 $ROOT/scripts/wm_canids.py --config $CI apply \$1 \$3 \$2 \$4 | grep -q 'FIRMWARE_RESTART' && [ \$(ls $CI | grep -c 'wm-before-match') = 2 ] && [ \$(diff -r $CI $T/ci0 2>/dev/null | grep -c '^< canbus_uuid') = 2 ] && python3 $ROOT/scripts/wm_canids.py --config $CI show | awk '{print \$2}' | tr '\\n' ' ' | grep -q \"^\$1 \$3 \$2 \$4 \\\$\" )"
check "canids script: applying the same ids again changes nothing" "( A=\$(python3 $ROOT/scripts/wm_canids.py --config $CI show | awk '{print \$2}'); set -- \$A; N=\$(ls $CI | wc -l); python3 $ROOT/scripts/wm_canids.py --config $CI apply \$1 \$2 \$3 \$4 | grep -q 'Nothing to change' && [ \$(ls $CI | wc -l) = \$N ] )"
check "canids script: refuses two equal ids and bad ids, changes nothing" "B=\$(cat $CI/wm_zru_thr0.cfg $CI/wm_zru_thr1.cfg $CI/wm_zru_thr2.cfg $CI/wm_zru_thr3.cfg | md5sum); ! python3 $ROOT/scripts/wm_canids.py --config $CI apply aaaaaaaaaaaa aaaaaaaaaaaa bbbbbbbbbbbb cccccccccccc && ! python3 $ROOT/scripts/wm_canids.py --config $CI apply zzzzzzzzzzzz 111111111111 222222222222 333333333333 && ! python3 $ROOT/scripts/wm_canids.py --config $CI apply 1 2 3 4 && [ \"\$(cat $CI/wm_zru_thr0.cfg $CI/wm_zru_thr1.cfg $CI/wm_zru_thr2.cfg $CI/wm_zru_thr3.cfg | md5sum)\" = \"\$B\" ]"
check "canids script: refuses when a file is missing" "mkdir -p $CI/gone && cp $CI/wm_zru_thr0.cfg $CI/wm_zru_thr1.cfg $CI/wm_zru_thr2.cfg $CI/gone/ && ! python3 $ROOT/scripts/wm_canids.py --config $CI/gone apply 111111111111 222222222222 333333333333 444444444444"
NZ="$T/nz"; mkdir -p "$NZ"; cp "$ROOT/factory/ultra-s/config/printer.cfg" "$ROOT/factory/ultra-s/config/tmt1.ini" "$NZ/"
check "nozzle script: show lists the four nozzles" "[ \$(python3 $ROOT/scripts/wm_nozzle.py --config $NZ show | grep -c '0.400000 mm') = 4 ]"
check "nozzle script: set changes only that nozzle's diameter and the type in tmt1.ini" "python3 $ROOT/scripts/wm_nozzle.py --config $NZ set 1 0.6 1 | grep -q 'Restart Klipper' && [ \$(diff $NZ/printer.cfg $ROOT/factory/ultra-s/config/printer.cfg | grep -c '^<') = 1 ] && python3 $ROOT/scripts/wm_nozzle.py --config $NZ show | grep -q 'Nozzle 2 (tool T1, \\[extruder1\\]): 0.600000' && grep -q '^type1=1' $NZ/tmt1.ini && grep -q '^type0=0' $NZ/tmt1.ini"
check "nozzle script: a copy of printer.cfg and tmt1.ini is kept first" "ls $NZ/printer.cfg.wm-before-nozzle-* $NZ/tmt1.ini.wm-before-nozzle-* && cmp \$(ls $NZ/printer.cfg.wm-before-nozzle-* | head -1) $ROOT/factory/ultra-s/config/printer.cfg"
check "nozzle script: refuses a tool, a diameter and a type that make no sense" "! python3 $ROOT/scripts/wm_nozzle.py --config $NZ set 4 0.4 && ! python3 $ROOT/scripts/wm_nozzle.py --config $NZ set 0 7 && ! python3 $ROOT/scripts/wm_nozzle.py --config $NZ set 0 0.4 5 && ! python3 $ROOT/scripts/wm_nozzle.py --config $NZ set 0 abc"
check "nozzle script: refuses a tool this printer does not have" "cp $ROOT/factory/ultra-s/config-variants/printer2.cfg $NZ/p2.cfg; mkdir -p $NZ/two; cp $NZ/p2.cfg $NZ/two/printer.cfg; ! python3 $ROOT/scripts/wm_nozzle.py --config $NZ/two set 3 0.4 | grep -v refused"
check "nozzle script: the SAVE_CONFIG block of printer.cfg is unchanged" "[ \"\$(sed -n '/SAVE_CONFIG/,\$p' $NZ/printer.cfg)\" = \"\$(sed -n '/SAVE_CONFIG/,\$p' $ROOT/factory/ultra-s/config/printer.cfg)\" ]"
NZ2="$T/nz2"; mkdir -p "$NZ2"; { cat "$ROOT/factory/ultra-s/config/printer.cfg" | sed '$d'; printf '#*# [extruder1]\n#*# nozzle_diameter = 0.400000\n'; } > "$NZ2/printer.cfg"
check "nozzle script: a nozzle_diameter that sits in the SAVE_CONFIG block is changed there too" "python3 $ROOT/scripts/wm_nozzle.py --config $NZ2 set 1 0.8 >/dev/null && grep -q '^#\\*# nozzle_diameter = 0.800000' $NZ2/printer.cfg"
HNZ="$T/hnz"; mkdir -p "$HNZ"; inst "$HNZ" --from-github --model ultra-s --shell-command off >/dev/null
check "nozzle: with the shell command extension off, rpi_nozzle.cfg is not installed or included" "[ ! -f $HNZ/printer_data/config/rpi_nozzle.cfg ] && ! grep -q 'wm_nozzle' $HNZ/printer_data/config/printer.cfg"
check "nozzle: and the doctor does not ask for it" "! yes n | WM_HOME=$HNZ WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'wm_nozzle'"
inst "$HNZ" --update --shell-command on >/dev/null
check "nozzle: turning the extension on installs rpi_nozzle.cfg and includes it" "[ -f $HNZ/printer_data/config/rpi_nozzle.cfg ] && grep -q '^\\[include rpi_nozzle.cfg\\]' $HNZ/printer_data/config/printer.cfg && [ -f $HNZ/klipper/klippy/extras/gcode_shell_command.py ]"
check "timelapse (F-232): with the shell command and timelapse on, rpi_timelapse.cfg is installed, included once, with its helper script" "cmp $ROOT/rpi-cfg/rpi_timelapse.cfg $HNZ/printer_data/config/rpi_timelapse.cfg && [ \$(grep -c '^\\[include rpi_timelapse.cfg\\]' $HNZ/printer_data/config/printer.cfg) = 1 ] && cmp $ROOT/scripts/wm_timelapse.py $HNZ/printer_data/wm-tools/wm_timelapse.py"
check "timelapse (F-232): the settings window macros and the helper exist" "grep -q '^\\[gcode_macro WM_TIMELAPSE\\]' $ROOT/rpi-cfg/rpi_timelapse.cfg && grep -q 'Save and restart' $ROOT/rpi-cfg/rpi_timelapse.cfg && python3 -I -m py_compile $ROOT/scripts/wm_timelapse.py"
check "nozzle: removing the shell command extension takes rpi_nozzle.cfg out of printer.cfg first" "M 'y\n' $HNZ --remove shell-command | grep -q 'Removed' && ! grep -q 'rpi_nozzle.cfg' $HNZ/printer_data/config/printer.cfg && ls $HNZ/printer_data/config/rpi_nozzle.cfg.wm-removed-* && [ ! -e $HNZ/klipper/klippy/extras/gcode_shell_command.py ]"

# Fluidd window macros (rpi_nozzle.cfg / rpi_calibration.cfg): mistakes found on a real printer
cat > "$T/macro_cycle.py" <<'PY'
import re, sys
macros = {}
for f in sys.argv[1:]:
    cur = None
    for line in open(f):
        m = re.match(r'\[gcode_macro\s+(\S+)\]', line)
        if m: cur = m.group(1); macros[cur] = set(); continue
        if line.startswith('['): cur = None; continue
        if cur and re.match(r'\s+[A-Za-z_][A-Za-z0-9_]*(\s|$)', line) and not line.lstrip().startswith(('#', 'RESPOND', 'SET_', 'SAVE_')):
            macros[cur].add(line.split()[0])
# calls that only run in a branch that cannot lead back: _WM_SETTER_DOWN calls _WM_SETTER_FIND only while the full offset calibration owns the setter (cal=1); _WM_SETTER_FIND_FAIL reaches _WM_SETTER_MOVE only when cal=0 (F-097, tested on the printer)
GUARDED = {('_WM_SETTER_DOWN', '_WM_SETTER_FIND')}
bad = []
def walk(n, path):
    for c in macros.get(n, ()):
        if (n, c) in GUARDED: continue
        if c in path: bad.append(' -> '.join(path + [c])); continue
        if c in macros: walk(c, path + [c])
for n in macros: walk(n, [n])
print('\n'.join(bad)); sys.exit(1 if bad else 0)
PY
check "windows: no ';' inside a RESPOND message (Klipper cuts the line there: Malformed command)" "! grep -n 'RESPOND.*MSG=.*;' $ROOT/rpi-cfg/*.cfg"
check "windows: no macro of ours calls itself, directly or through others (Klipper: called recursively)" "python3 -I $T/macro_cycle.py $ROOT/rpi-cfg/rpi_nozzle.cfg $ROOT/rpi-cfg/rpi_calibration.cfg $ROOT/rpi-cfg/rpi_base.cfg"
check "windows: the cycle test really catches a loop" "printf '[gcode_macro A]\ngcode:\n    B\n[gcode_macro B]\ngcode:\n    A\n' > $T/loop.cfg; ! python3 -I $T/macro_cycle.py $T/loop.cfg"
check "windows: Extruder Setup matching goes from tool to tool through a delayed gcode" "grep -q '^\\[delayed_gcode _WM_MATCH_NEXT\\]' $ROOT/rpi-cfg/rpi_nozzle.cfg && grep -q 'UPDATE_DELAYED_GCODE ID=_WM_MATCH_NEXT' $ROOT/rpi-cfg/rpi_nozzle.cfg && grep -q '^variable_next: 0' $ROOT/rpi-cfg/rpi_nozzle.cfg"
check "windows: both start checks show a Fluidd window before they stop" "python3 -I $ROOT/tests/check_windows.py checks"
check "windows: Restart Klipper now closes the window first" "grep -q 'Restart Klipper now|_WM_RESTART_KLIPPER|primary' $ROOT/rpi-cfg/rpi_nozzle.cfg && python3 -I $ROOT/tests/check_windows.py restart"
rm -f "$G2"/klipper/klippy/extras/cs1237.*.so
check "doctor finds a missing module and restores it from the repo" "WM_HOME=$G2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --doctor; ls $G2/klipper/klippy/extras/cs1237.*.so"
check "doctor reports bad network clock/power as problems" "! WM_TEST_THROTTLED=0x50005 WM_HOME=$G2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --doctor"
printf '[update_manager]\npassword: hunter2\nhost: 192.168.7.44\n' >> "$G2/printer_data/config/moonraker.conf"
WM_HOME="$G2" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --support-bundle >/dev/null 2>&1
SB="$(ls $G2/wm-support-*.tgz | head -1)"
check "support bundle made" "[ -f $SB ]"
check "support bundle has no password or private IP" "! tar xzOf $SB | grep -Eq 'hunter2|192\\.168\\.7\\.44'"
check "support bundle report has the USB tree and serial port sections" "tar xzOf $SB | grep -q \"usb tree\" && tar xzOf $SB | grep -q \"serial ports Klipper's python sees\""
check "support bundle has no calibration database or gcodes" "! tar tzf $SB | grep -Eq 'database|gcodes|\\.gcode'"

sec "== pre-flight"
check "no internet: install refused before changing anything" "! WM_TEST_NO_NET=1 WM_HOME=$T/pf WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --from-github --model ultra && [ ! -d $T/pf/klipper ]"
check "under-voltage is reported" "WM_TEST_THROTTLED=0x50005 WM_TEST_CANQUERY=$T/can_ok.txt inst $T/pf2 --from-github --model ultra | grep -q 'under-voltage'"

sec "== panel comes from the panel repository"
mkdir -p "$T/pnl"; python3 - "$T/pnl/fluidd-new.zip" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1], "w"); z.writestr("index.html", "<html>NEWEST-PANEL</html>"); z.close()
PY
P1="$T/p1"; mkdir -p "$P1"; WM_TEST_PANEL_DIR="$T/pnl" inst "$P1" --from-github --model ultra --no-start > "$T/p1.out"
check "newest panel from the panel repository is installed" "grep -q NEWEST-PANEL $P1/fluidd/index.html && grep -q 'panel repository' $T/p1.out"
P2="$T/p2"; mkdir -p "$P2"; inst "$P2" --from-github --model ultra --no-start > "$T/p2.out"
check "default test panel installed" "grep -q -i fluidd $P2/fluidd/index.html"
P3="$T/p3"; mkdir -p "$P3"; WM_TEST_PANEL_DIR="$T/nonexistent" WM_HOME="$P3" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --from-github --model ultra --no-start > "$T/p3.out" 2>&1
check "panel download fails: install goes on, tells how to retry" "[ -d $P3/klipper/klippy ] && [ ! -f $P3/fluidd/index.html ] && grep -q 'installer.sh --update' $T/p3.out"
inst "$P2" --update > "$T/p2u.out"
check "update: panel already latest, nothing replaced" "grep -q 'already the latest' $T/p2u.out"
WM_TEST_PANEL_DIR="$T/pnl" inst "$P2" --update > "$T/p2v.out"
check "update: a changed panel in the panel repository is installed" "grep -q NEWEST-PANEL $P2/fluidd/index.html"
check "update: only one copy of the old Fluidd is kept" "[ \$(ls -d $P2/wm-rpi-backup/fluidd-* | wc -l) = 1 ] && [ ! -e $P2/fluidd.new ]"
mkdir -p "$T/pnlbad"; python3 - "$T/pnlbad/fluidd-bad.zip" <<'PY'
import sys, zipfile
z = zipfile.ZipFile(sys.argv[1], "w", zipfile.ZIP_STORED); z.writestr("index.html", "<html>BROKEN-PANEL-CONTENT</html>"); z.close()
d = bytearray(open(sys.argv[1], "rb").read()); i = d.index(b"BROKEN"); d[i] = ord("X"); open(sys.argv[1], "wb").write(d)
PY
WM_TEST_PANEL_DIR="$T/pnlbad" inst "$P2" --update > "$T/p2w.out" 2>&1
check "update: a damaged panel zip leaves the old Fluidd untouched and says so" "grep -q NEWEST-PANEL $P2/fluidd/index.html && [ ! -e $P2/fluidd.new ] && grep -q 'NOT updated' $T/p2w.out"

sec "== screen removal on the Pi"
inst2 "$H3" --update > "$T/rm.out" 2>&1   # F-234: no --screen-remove any more; the update removes it
check "screen-remove: folder and service gone" "[ ! -d $H3/KlipperScreen ] && grep -q 'systemctl disable KlipperScreen' $H3/.sudo.log"
check "screen-remove: answers keep only the macros" "grep -q WANT_SCREEN=macros $H3/wm-rpi-backup/install.conf"
check "screen-remove: Klipper stays (macros kept)" "[ -f $H3/printer_data/config/zr_tools.cfg ] && [ -d $H3/klipper ]"

sec "== screen board script (factory screen as KlipperScreen)"
SB="$ROOT/scripts/screen_board.sh"
sb() { local h="$1"; shift; WM_TEST_SERVICES="${WM_TEST_SERVICES-makerbase-client klipper moonraker nginx crowsnest janus hostapd klipper-mcu makerbase-webcam}" WM_HOME="$h" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$SB" "$@" 2>&1; }
check "board script syntax" "bash -n $SB"
B1="$T/b1"; mkdir -p "$B1/printer_data/config"
sb "$B1" --pi wmpi.local > "$T/b1.out"
check "board: factory services stopped and disabled" "[ ! -e $B1/.svc/makerbase-client.active ] && [ ! -e $B1/.svc/klipper.enabled ] && [ ! -e $B1/.svc/nginx.enabled ]"
check "board: ssh/network services untouched (not in list)" "! grep -q 'systemctl stop ssh' $B1/.sudo.log"
check "board: previous state saved" "grep -q 'makerbase-client enabled active' $B1/wm-screen-backup/disabled.list"
check "board: KlipperScreen config points at the Pi" "grep -q 'moonraker_host: wmpi.local' $B1/printer_data/config/KlipperScreen.conf"
check "board: printer is named WonderMaker and the size defaults to comfortable" "grep -q '^\[printer WonderMaker\]' $B1/printer_data/config/KlipperScreen.conf && grep -q 'density = comfortable' $B1/printer_data/config/zr_screen.conf"
check "board: ZR Tools files copied" "[ -f $B1/KlipperScreen/panels/zr_tools.py ] && [ -f $B1/KlipperScreen/panels/zr_logic.py ]"
check "board: uses pinned KlipperScreen commit" "grep -q '34610ceae31e12a10cc980e20a1dec9976f97dd4' $B1/.sudo.log"

# the board side
SBC="$T/sbc"; mkdir -p "$SBC/printer_data/config" "$T/sbc_v4l"
check "board camera: no camera plugged in says so and writes nothing" "sb $SBC --camera | grep -q 'No camera plugged into this board' && [ ! -f $SBC/printer_data/config/crowsnest.conf ]"
touch "$T/sbc_v4l/usb-Fake_Cam-video-index0"
check "board camera: a camera enables crowsnest at 720p 30 fps on port 8080, no_proxy true" "WM_V4L_BYID_DIR=$T/sbc_v4l sb $SBC --camera >/dev/null; grep -q 'wm-screen-camera' $SBC/printer_data/config/crowsnest.conf && grep -q '^port: 8080' $SBC/printer_data/config/crowsnest.conf && grep -q '^resolution: 1280x720' $SBC/printer_data/config/crowsnest.conf && grep -q '^max_fps: 30' $SBC/printer_data/config/crowsnest.conf && grep -q '^no_proxy: true' $SBC/printer_data/config/crowsnest.conf && grep -q 'usb-Fake_Cam-video-index0' $SBC/printer_data/config/crowsnest.conf && grep -q 'enable --now crowsnest' $SBC/.sudo.log"
printf '[cam mine]\nmode: ustreamer\nport: 8090\ndevice: /dev/video9\n' > "$SBC/printer_data/config/crowsnest.conf"
check "board camera: a crowsnest.conf you wrote yourself is kept, with a warning" "WM_V4L_BYID_DIR=$T/sbc_v4l sb $SBC --camera | grep -q 'is kept' && grep -q 'device: /dev/video9' $SBC/printer_data/config/crowsnest.conf && ls $SBC/printer_data/config/crowsnest.conf.wm-before-screen-camera-* >/dev/null"
printf '#### This is a typical default config.\n[crowsnest]\nno_proxy: false\n[cam 1]\nport: 8080\n' > "$SBC/printer_data/config/crowsnest.conf"
check "board camera: crowsnest's own default file is replaced, a copy is kept" "WM_V4L_BYID_DIR=$T/sbc_v4l sb $SBC --camera >/dev/null; grep -q 'wm-screen-camera' $SBC/printer_data/config/crowsnest.conf && ls $SBC/printer_data/config/crowsnest.conf.wm-before-screen-camera-* >/dev/null"
check "board camera: the board service announces the camera (rpi_screen_camera.json) and has the --camera option" "grep -q 'rpi_screen_camera.json' $ROOT/zr_tools/wm-chamber-light-http && grep -q -- '--camera' $SB"

sec "== 2.19.0: ZR Tools screen changes (F-137)"
check "F-137: KlipperScreen changes apply once and never twice, the panel files compile and carry the new design" "python3 -I $ROOT/tests/test_f137.py $ROOT"
SPL="$T/spl"; mkdir -p "$SPL/printer_data/config"; printf '[printer WonderMaker]\nmoonraker_host: x\n\n#~# --- Do not edit below this line. This section is saved automatically. ---\n#~# [main]\n#~# language = en\n' > "$SPL/printer_data/config/KlipperScreen.conf"
check "F-137: the Connecting screen menu gets ZR Tools once, above KlipperScreen's own saved section" "sed -n '/^ks_splash_zr_menu()/,/^}/p' $SB > $T/spl_fn.sh; CFG_DIR=$SPL/printer_data/config; . $T/spl_fn.sh; ks_splash_zr_menu; ks_splash_zr_menu; [ \$(grep -c '__splashscreen zr_tools' \$CFG_DIR/KlipperScreen.conf) = 1 ] && awk '/__splashscreen zr_tools/{a=NR} /^#~# ---/{b=NR} END{exit !(a<b)}' \$CFG_DIR/KlipperScreen.conf && grep -q '#~# language = en' \$CFG_DIR/KlipperScreen.conf"
check "F-137: a new board install writes the ZR Tools entry for the Connecting screen" "grep -q 'menu __splashscreen zr_tools' $SB"


sec "== menu: Update now reopens the menu on the new version"
UN="$T/un"; mkdir -p "$UN/new" "$UN/home/printer_data/config" "$UN/bh/printer_data/config" "$UN/bh/KlipperScreen"
cp -a "$ROOT/." "$UN/new/"; rm -rf "$UN/new/.git"; echo 9.9.9 > "$UN/new/VERSION"; echo S9.9.9 > "$UN/new/SCREEN_VERSION"
cp -a "$UN/new" "$UN/oldpi"; echo "$(cat $ROOT/VERSION)" > "$UN/oldpi/VERSION"
check "Pi menu: Update now with nothing installed still reopens on the new version" "printf '2\n2\ny\n0\n0\n' | WM_TEST_NO_FETCH=1 WM_HOME=$UN/home WM_INSTALLER_TEST=1 WM_TEST_UPDATE_DIR=$UN/new bash $UN/oldpi/installer.sh --menu 2>&1 | grep -q 'installer 9.9.9'"
cp -a "$UN/new" "$UN/oldb"; echo "$(cat $ROOT/VERSION)" > "$UN/oldb/VERSION"
check "board menu: Update now reopens on the new version even when there is nothing to back up" "printf '2\n2\ny\n0\n0\n' | WM_TEST_REFRESH_REPO=1 WM_HOME=$UN/bh WM_INSTALLER_TEST=1 WM_TEST_UPDATE_DIR=$UN/new bash $UN/oldb/scripts/screen_board.sh --menu 2>&1 | grep -q 'installer 9.9.9'"

check "board menu: Update now with no KlipperScreen updates the installer files and reopens on the new version" "rm -f $UN/bh/KlipperScreen/panels/zr_screen_version.txt $UN/bh/wm-screen-backup/screen_version; rm -rf $UN/oldb2; cp -a $UN/new $UN/oldb2; echo 1.0.0 > $UN/oldb2/VERSION; echo S1.0.0 > $UN/oldb2/SCREEN_VERSION; printf '2\n2\ny\n0\n0\n' | WM_TEST_NO_KS=1 WM_TEST_REFRESH_REPO=1 WM_HOME=$UN/bh WM_INSTALLER_TEST=1 WM_TEST_UPDATE_DIR=$UN/new bash $UN/oldb2/scripts/screen_board.sh --menu 2>&1 | tee $UN/nok.out | grep -q 'installer 9.9.9' && grep -q 'not installed on this board yet' $UN/nok.out && ! grep -q \"Can't continue\" $UN/nok.out"
sec "== free up disk space (screen board)"
FSB="$T/fsb"; FST="$T/fst"; mkdir -p "$FSB/.cache/pip" "$FSB/printer_data/config" "$FSB/printer_data/logs" "$FSB/printer_data/gcodes" "$FST/tmp.AAA/scripts" "$FST/tmp.keep" "$FSB/wm_ultra_vanilla_klipper"
dd if=/dev/zero of="$FSB/.cache/pip/x" bs=1M count=3 2>/dev/null; dd if=/dev/zero of="$FST/tmp.AAA/pad" bs=1M count=3 2>/dev/null
echo 1.0.0 > "$FST/tmp.AAA/VERSION"; touch "$FST/tmp.AAA/scripts/screen_board.sh"; echo mine > "$FST/tmp.keep/file"; echo gcode > "$FSB/printer_data/gcodes/a.gcode"
fsb() { local ans="$1"; shift; printf "$ans" | WM_TEST_TMP="$FST" WM_HOME="$FSB" WM_INSTALLER_TEST=1 WM_TEST_APT_KB=204800 WM_TEST_JOURNAL_KB=102400 "$@" bash "$SB" --free-space 2>&1; }
check "free space: lists what can go, with warnings and sizes" "fsb '\n' env | grep -q 'Leftover installer downloads' && fsb '\n' env | grep -q 'apt package cache' && fsb '\n' env | grep -q 'never in this list'"
check "free space: Enter cancels and erases nothing" "fsb '\n' env >/dev/null; [ -d $FST/tmp.AAA ] && [ -d $FSB/.cache/pip ]"
check "free space: answering no at the confirmation erases nothing" "fsb '1\nn\n' env | grep -q 'This will ERASE'; [ -d $FST/tmp.AAA ]"
check "free space: the warning is shown before the confirmation" "fsb '1\nn\n' env | grep -q 'Copies of this installer'"
check "free space: erases only the chosen item after confirming" "printf '1\ny\n' | WM_TEST_TMP=$FST WM_HOME=$FSB WM_INSTALLER_TEST=1 bash $SB --free-space >/dev/null 2>&1; [ ! -d $FST/tmp.AAA ] && [ -d $FST/tmp.keep ] && [ -d $FSB/.cache/pip ] && [ -f $FSB/printer_data/gcodes/a.gcode ]"
check "free space: tests never offer the real repository's .git for erasing" "fsb '\n' env | grep -qv 'Git history'"
check "free space: the git history is offered (and erased) only on a copy of the installer folder" "rm -rf $T/gcopy; mkdir -p $T/gcopy/wm_ultra_vanilla_klipper/scripts; cp $SB $ROOT/scripts/lib_free_space.sh $T/gcopy/wm_ultra_vanilla_klipper/scripts/; cp $ROOT/VERSION $T/gcopy/wm_ultra_vanilla_klipper/; mkdir -p $T/gcopy/wm_ultra_vanilla_klipper/.git; dd if=/dev/zero of=$T/gcopy/wm_ultra_vanilla_klipper/.git/pack bs=1M count=3 2>/dev/null; printf 'all\ny\n' | WM_TEST_REFRESH_REPO=1 WM_TEST_TMP=$FST WM_HOME=$FSB WM_INSTALLER_TEST=1 bash $T/gcopy/wm_ultra_vanilla_klipper/scripts/screen_board.sh --free-space > $T/gcopy.out 2>&1; grep -q 'Git history' $T/gcopy.out && [ ! -d $T/gcopy/wm_ultra_vanilla_klipper/.git ] && [ -d $ROOT/.git ]"
check "free space: sudo items go through sudo (apt clean, journal vacuum)" "printf 'all\ny\n' | WM_TEST_TMP=$FST WM_HOME=$FSB WM_INSTALLER_TEST=1 WM_TEST_APT_KB=204800 WM_TEST_JOURNAL_KB=102400 bash $SB --free-space >/dev/null 2>&1; grep -q 'apt-get clean' $FSB/.sudo.log && grep -q 'vacuum-size=50M' $FSB/.sudo.log && [ ! -d $FSB/.cache/pip ] && [ -f $FSB/printer_data/gcodes/a.gcode ]"
check "free space: --yes alone never erases (confirmation defaults to no)" "mkdir -p $FSB/.cache/pip; dd if=/dev/zero of=$FSB/.cache/pip/x bs=1M count=3 2>/dev/null; WM_ASSUME_YES=1 WM_TEST_TMP=$FST WM_HOME=$FSB WM_INSTALLER_TEST=1 bash $SB --free-space >/dev/null 2>&1; [ -d $FSB/.cache/pip ]"
check "board Uninstall menu has Free up disk space" "printf '9\n0\n0\n' | WM_HOME=$FSB WM_INSTALLER_TEST=1 bash $SB --menu 2>&1 | grep -q 'Free up disk space'"
FSI="$T/fsi"; mkdir -p "$FSI/.cache/pip" "$FSI/printer_data/config"; dd if=/dev/zero of="$FSI/.cache/pip/x" bs=1M count=3 2>/dev/null
printf 'y\n1\ny\ny\n' | WM_TEST_FREE_OFFER=1 WM_TEST_DISK_MB=1499 WM_TEST_TMP=$FST WM_HOME=$FSI WM_INSTALLER_TEST=1 bash $SB --install --pi 192.0.2.5 --no-reboot > $T/fsi.out 2>&1
check "install: not enough space offers the cleanup, warns, then goes on" "grep -q 'Only 1499 MB free' $T/fsi.out && grep -q 'This will ERASE' $T/fsi.out && grep -q 'disk space' $T/fsi.out"
check "board script never calls a missing helper" "! grep -q 'command not found' $T/fsi.out"
check "install: still too little space after the cleanup stops with the --free-space hint" "printf 'n\n' | WM_TEST_FREE_OFFER=1 WM_TEST_DISK_MB=1000 WM_TEST_TMP=$FST WM_HOME=$T/fsi2 WM_INSTALLER_TEST=1 bash $SB --install --pi 192.0.2.5 --no-reboot 2>&1 | grep -q 'free-space'"
check "install: no terminal and not enough space stops without asking" "! WM_TEST_DISK_MB=1000 WM_HOME=$T/fsi3 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --install --pi 192.0.2.5 --no-reboot >/dev/null 2>&1"

sec "== free up disk space (Pi installer)"
PFB="$T/pfb"; PFT="$T/pft"; mkdir -p "$PFB/.cache/pip" "$PFB/printer_data/logs" "$PFB/printer_data/gcodes" "$PFT/tmp.AAA/scripts" "$PFT/tmp.keep"
dd if=/dev/zero of="$PFB/.cache/pip/x" bs=1M count=3 2>/dev/null; dd if=/dev/zero of="$PFT/tmp.AAA/pad" bs=1M count=3 2>/dev/null
echo 1.0.0 > "$PFT/tmp.AAA/VERSION"; touch "$PFT/tmp.AAA/scripts/screen_board.sh"; echo mine > "$PFT/tmp.keep/file"; echo gcode > "$PFB/printer_data/gcodes/a.gcode"; echo old > "$PFB/printer_data/logs/klippy.log.1"; dd if=/dev/zero of="$PFB/printer_data/logs/klippy.log.1" bs=1M count=2 2>/dev/null
pfs() { local ans="$1"; shift; printf "$ans" | WM_TEST_NO_FETCH=1 WM_TEST_TMP="$PFT" WM_HOME="$PFB" WM_INSTALLER_TEST=1 WM_TEST_APT_KB=204800 WM_TEST_JOURNAL_KB=102400 "$@" bash "$ROOT/installer.sh" --free-space 2>&1; }
pfs '\n' env > $T/pfs1.out
check "Pi free space: lists what can go, with sizes and warnings" "grep -q 'Leftover installer downloads' $T/pfs1.out && grep -q 'apt package cache' $T/pfs1.out && grep -q 'Old rotated printer logs' $T/pfs1.out && grep -q 'never in this list' $T/pfs1.out"
check "Pi free space: Enter cancels and erases nothing" "[ -d $PFT/tmp.AAA ] && [ -d $PFB/.cache/pip ] && [ -f $PFB/printer_data/logs/klippy.log.1 ]"
pfs '1\nn\n' env > $T/pfs2.out
check "Pi free space: the warning and 'This will ERASE' come before the confirmation, and 'no' erases nothing" "grep -q 'This will ERASE' $T/pfs2.out && grep -q 'Copies of this installer' $T/pfs2.out && [ -d $PFT/tmp.AAA ]"
check "Pi free space: erases only the chosen item after confirming" "printf '1\ny\n' | WM_TEST_TMP=$PFT WM_HOME=$PFB WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --free-space >/dev/null 2>&1; [ ! -d $PFT/tmp.AAA ] && [ -d $PFT/tmp.keep ] && [ -d $PFB/.cache/pip ] && [ -f $PFB/printer_data/gcodes/a.gcode ]"
check "Pi free space: all goes through sudo for apt and the journal and keeps gcode files" "printf 'all\ny\n' | WM_TEST_TMP=$PFT WM_HOME=$PFB WM_INSTALLER_TEST=1 WM_TEST_APT_KB=204800 WM_TEST_JOURNAL_KB=102400 bash $ROOT/installer.sh --free-space >/dev/null 2>&1; grep -q 'apt-get clean' $PFB/.sudo.log && grep -q 'vacuum-size=50M' $PFB/.sudo.log && [ ! -d $PFB/.cache/pip ] && [ ! -f $PFB/printer_data/logs/klippy.log.1 ] && [ -f $PFB/printer_data/gcodes/a.gcode ] && [ -d $ROOT/.git ]"
check "Pi free space: --yes alone never erases" "mkdir -p $PFB/.cache/pip; dd if=/dev/zero of=$PFB/.cache/pip/x bs=1M count=3 2>/dev/null; WM_ASSUME_YES=1 WM_TEST_TMP=$PFT WM_HOME=$PFB WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --free-space >/dev/null 2>&1; [ -d $PFB/.cache/pip ]"
check "Pi free space: the git history is offered only on a copy of the installer folder" "rm -rf $T/pgcopy; mkdir -p $T/pgcopy/wm_ultra_vanilla_klipper/.git; cp $ROOT/installer.sh $ROOT/VERSION $T/pgcopy/wm_ultra_vanilla_klipper/; mkdir -p $T/pgcopy/wm_ultra_vanilla_klipper/scripts; cp $ROOT/scripts/lib_free_space.sh $T/pgcopy/wm_ultra_vanilla_klipper/scripts/; dd if=/dev/zero of=$T/pgcopy/wm_ultra_vanilla_klipper/.git/pack bs=1M count=3 2>/dev/null; printf 'all\ny\n' | WM_TEST_REFRESH_REPO=1 WM_TEST_TMP=$PFT WM_HOME=$PFB WM_INSTALLER_TEST=1 bash $T/pgcopy/wm_ultra_vanilla_klipper/installer.sh --free-space > $T/pgcopy.out 2>&1; grep -q 'Git history' $T/pgcopy.out && [ ! -d $T/pgcopy/wm_ultra_vanilla_klipper/.git ] && [ -d $ROOT/.git ]; ! pfs '\n' env | grep -q 'Git history'"
check "Pi Uninstall menu has Free up disk space" "printf '6\n0\n0\n' | WM_TEST_NO_FETCH=1 WM_HOME=$PFB WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --menu 2>&1 | grep -q 'Free up disk space'"
check "Pi install: no terminal and not enough space stops with the --free-space hint" "WM_TEST_DISK_MB=1000 WM_HOME=$T/pfi1 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --from-github --model ultra-s 2>&1 </dev/null | grep -q 'free-space'"
mkdir -p "$T/pfi2/.cache/pip"; dd if=/dev/zero of="$T/pfi2/.cache/pip/x" bs=1M count=3 2>/dev/null
printf 'y\n1\ny\n' | WM_TEST_FREE_OFFER=1 WM_TEST_DISK_MB=2499 WM_TEST_TMP=$PFT WM_HOME=$T/pfi2 WM_INSTALLER_TEST=1 timeout 100 bash $ROOT/installer.sh --from-github --model ultra-s > $T/pfi2.out 2>&1
check "Pi install: not enough space offers the cleanup, warns, then goes on" "grep -q 'Only 2499 MB free' $T/pfi2.out && grep -q 'This will ERASE' $T/pfi2.out && grep -q 'Disk space ok' $T/pfi2.out"

sec "== ZR Tools on the Pi, and the clock fix"
mkpi() { local h="$1"; mkdir -p "$h/printer_data/config"; printf '[include mainsail.cfg]\n\n[save_variables]\nfilename: /tmp/v.cfg\n\n#*# <---- SAVE_CONFIG ---->\n' > "$h/printer_data/config/printer.cfg"; }
PZ="$T/pz"; mkpi "$PZ"
zr() { WM_TEST_NO_FETCH=1 WM_HOME="$PZ" WM_INSTALLER_TEST=1 "$@" bash "$ROOT/installer.sh" --zr-tools 2>&1; }
check "Pi --zr-tools: installs the macros when they are missing" "env | true; zr env | grep -q 'installed and configured' && [ -f $PZ/printer_data/config/zr_tools.cfg ] && grep -q '^\[include zr_tools.cfg\]' $PZ/printer_data/config/printer.cfg"
check "Pi --zr-tools: second run says already installed and changes nothing" "zr env | grep -q 'already installed' && [ \$(grep -c 'include zr_tools.cfg' $PZ/printer_data/config/printer.cfg) = 1 ]"
check "Pi --zr-tools: an edited zr_tools.cfg with every macro counts as installed and is kept" "echo '# mine' >> $PZ/printer_data/config/zr_tools.cfg; zr env | grep -q 'already installed' && grep -q '^# mine' $PZ/printer_data/config/zr_tools.cfg"
check "Pi --zr-tools: a zr_tools.cfg that lost a macro is replaced (old copy kept)" "sed -i '0,/^\\[gcode_macro _\\?ZR_/s//[gcode_macro NOT_ZR_/' $PZ/printer_data/config/zr_tools.cfg; zr env | grep -q 'installed and configured' && ls $PZ/printer_data/config/ | grep -q 'zr_tools.cfg.zrbak_'"
check "Pi --zr-tools: ZR_REPLACE=1 replaces an edited file with the bundled copy" "echo '# mine2' >> $PZ/printer_data/config/zr_tools.cfg; zr env ZR_REPLACE=1 | grep -q 'installed and configured' && ! grep -q '^# mine2' $PZ/printer_data/config/zr_tools.cfg"
PZ2="$T/pz2"; mkpi "$PZ2"; sed -i '/save_variables/,/^$/d' "$PZ2/printer_data/config/printer.cfg"
check "Pi --zr-tools: adds [save_variables] when no config file has one" "WM_TEST_NO_FETCH=1 WM_HOME=$PZ2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --zr-tools >/dev/null 2>&1; grep -q '^\[save_variables\]' $PZ2/printer_data/config/printer.cfg"
PZ3="$T/pz3"; mkpi "$PZ3"
check "Pi --zr-tools: refuses during a print and changes nothing" "WM_TEST_NO_FETCH=1 WM_TEST_PRINT_STATE=printing WM_HOME=$PZ3 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --zr-tools 2>&1 | grep -q 'print is running'; [ ! -f $PZ3/printer_data/config/zr_tools.cfg ]"
check "Pi --zr-tools: without printer.cfg it explains and fails" "! WM_TEST_NO_FETCH=1 WM_HOME=$T/nopz WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --zr-tools >/dev/null 2>&1"
check "Pi --zr-tools --dry-run changes nothing" "PZ4=$T/pz4; mkdir -p \$PZ4/printer_data/config; cp $PZ3/printer_data/config/printer.cfg \$PZ4/printer_data/config/; WM_HOME=\$PZ4 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --zr-tools --dry-run >/dev/null 2>&1; [ ! -f \$PZ4/printer_data/config/zr_tools.cfg ]"
check "Pi Add-ons menu lists the ZR Tools macros" "printf '3\n0\n0\n' | WM_TEST_NO_FETCH=1 WM_HOME=$PZ3 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --menu 2>&1 | grep -q 'ZR Tools macros'"

BP="$T/bzp"; PIH="$T/pih"; mkpi "$PIH"; mkdir -p "$BP/printer_data/config"
zrp() { WM_TEST_PI_HOME="$PIH" WM_HOME="$BP" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 "$@" bash "$SB" --zr-pi --pi 192.0.2.5 2>&1; }
check "board --zr-pi: installs the macros on the Pi when missing" "zrp env | grep -q 'installed and configured on the Pi' && [ -f $PIH/printer_data/config/zr_tools.cfg ]"
check "board --zr-pi: second run says already installed" "zrp env | grep -q 'already installed on the Pi'"
check "board --zr-pi: Klipper on the Pi is restarted only after a change" "rm -f $BP/.sudo.log; zrp env >/dev/null; ! grep -q 'restart klipper on' $BP/.sudo.log"
check "board --zr-pi: a wrong password is explained" "zrp env WM_TEST_PI_PASS=wrong | grep -q 'refused the user name or password'"
check "board --zr-pi: a print on the Pi blocks it" "rm -rf $PIH/printer_data/config/zr_tools.cfg; zrp env WM_TEST_PI_PRINT_STATE=printing | grep -q 'not installed there'; [ ! -f $PIH/printer_data/config/zr_tools.cfg ]"
check "board --zr-pi: the password is never written to a file" "rm -f $PIH/printer_data/config/zr_tools.cfg; zrp env WM_TEST_PI_PASS=s3cretPW >/dev/null; ! grep -rqF s3cretPW $BP"
# install: the question defaults to no, yes runs it
BQ="$T/bq"; mkdir -p "$BQ/printer_data/config"; PIQ="$T/piq"; mkpi "$PIQ"
check "board install: the ZR Tools question defaults to no" "sb $BQ --pi 192.0.2.5 | grep -q 'ZR Tools page needs its macros on the Pi' && [ ! -f $PIQ/printer_data/config/zr_tools.cfg ]"
BQ2="$T/bq2"; mkdir -p "$BQ2/printer_data/config"
check "board install: answering yes sets up the macros on the Pi" "printf 'y\ny\ny\ny\ny\n' | WM_TEST_PI_HOME=$PIQ WM_HOME=$BQ2 WM_INSTALLER_TEST=1 bash $SB --install --pi 192.0.2.5 --no-reboot 2>&1 | grep -q 'installed and configured on the Pi' && [ -f $PIQ/printer_data/config/zr_tools.cfg ]"
check "board install --dry-run mentions ZR Tools on the Pi and changes nothing" "BQ3=$T/bq3; mkdir -p \$BQ3; sb \$BQ3 --pi 192.0.2.5 --dry-run | grep -q 'ZR Tools macros on the Pi'; [ ! -f $T/bq3/.sudo.log ] || ! grep -q 'timedatectl' $T/bq3/.sudo.log"
check "board install: turns on automatic time sync when the clock is not synced" "grep -q 'timedatectl set-ntp true' $B1/.sudo.log"
BC="$T/bc"; mkdir -p "$BC/printer_data/config"
check "free space: one shared file, loaded by both the Pi installer and the board" "[ -f $ROOT/scripts/lib_free_space.sh ] && grep -q 'lib_free_space.sh' $ROOT/installer.sh && grep -q 'lib_free_space.sh' $ROOT/scripts/screen_board.sh && ! grep -q '^fs_scan()' $ROOT/installer.sh $ROOT/scripts/screen_board.sh"
check "board clock: no curl -k anywhere" "! grep -q 'curl -sIk' $ROOT/scripts/screen_board.sh"
NB="$T/ntp1"; mkdir -p "$NB"
check "board clock: asks, remembers the yes, and does not ask again within the hour" "WM_HOME=$NB WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --fix-clock >/dev/null 2>&1; [ -f $NB/.wm-ntp-asked ] && WM_HOME=$NB WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --fix-clock 2>&1 | grep -q 'Not asking again'"
TZB="$T/tzb"; mkdir -p "$TZB"
check "board --set-tz sets the zone" "WM_TEST_TZ=Asia/Shanghai WM_HOME=$TZB WM_INSTALLER_TEST=1 bash $SB --set-tz America/Toronto 2>&1 | grep -q 'Time zone is America/Toronto (was Asia/Shanghai)'; grep -q 'timedatectl set-timezone America/Toronto' $TZB/.sudo.log"
check "board --set-tz refuses a name that is not a zone" "WM_TEST_TZ=Asia/Shanghai WM_HOME=$TZB WM_INSTALLER_TEST=1 bash $SB --set-tz 'bad zone;x' 2>&1 | grep -q 'not a time zone name'"
check "board --set-tz without a name asks, Enter keeps it" "BEFORE=\$(grep -c set-timezone $TZB/.sudo.log); printf '\n' | WM_TEST_TZ=Asia/Shanghai WM_HOME=$TZB WM_INSTALLER_TEST=1 bash $SB --set-tz 2>&1 | grep -q 'left as Asia/Shanghai'; [ \$(grep -c set-timezone $TZB/.sudo.log) = \$BEFORE ]"
check "board --set-tz --dry-run changes nothing" "BEFORE=\$(grep -c set-timezone $TZB/.sudo.log); WM_TEST_TZ=Asia/Shanghai WM_HOME=$TZB WM_INSTALLER_TEST=1 bash $SB --set-tz Europe/Paris --dry-run 2>&1 | grep -q 'would run: sudo timedatectl set-timezone Europe/Paris'; [ \$(grep -c set-timezone $TZB/.sudo.log) = \$BEFORE ]"
check "board --set-tz: a board on the zone already is left alone" "BEFORE=\$(grep -c set-timezone $TZB/.sudo.log); WM_TEST_TZ=America/Toronto WM_HOME=$TZB WM_INSTALLER_TEST=1 bash $SB --set-tz America/Toronto 2>&1 | grep -q 'Time zone is America/Toronto'; [ \$(grep -c set-timezone $TZB/.sudo.log) = \$BEFORE ]"
check "board --help names --set-tz" "grep -q -- '--set-tz America/Toronto' $SB"
check "board clock: asks again after an hour" "echo 1 > $NB/.wm-ntp-asked; WM_HOME=$NB WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --fix-clock 2>&1 | grep -q 'Automatic time sync is on'"
check "board --fix-clock: nothing to do when NTP is already synchronised" "WM_TEST_NTP_SYNCED=yes WM_HOME=$BC WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --fix-clock 2>&1 | grep -q 'set automatically'; ! grep -q 'timedatectl' $BC/.sudo.log 2>/dev/null"
check "board --fix-clock: falls back to GitHub's date when NTP finds no server" "WM_TEST_NTP_FAIL=1 WM_HOME=$BC WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --fix-clock >/dev/null 2>&1; grep -q 'date -s' $BC/.sudo.log"
check "board Settings menu has the ZR Tools and clock entries" "printf '5\n0\n0\n' | WM_HOME=$BC WM_INSTALLER_TEST=1 bash $SB --menu 2>&1 | grep -q 'Set up ZR Tools on the Pi' && printf '5\n0\n0\n' | WM_HOME=$BC WM_INSTALLER_TEST=1 bash $SB --menu 2>&1 | grep -q 'Fix the clock'"
check "board: installs with apt-get install --no-upgrade, never upgrade" "grep -q 'apt-get install -y --no-upgrade' $B1/.sudo.log && ! grep -q -E 'apt(-get)? (dist-)?upgrade' $B1/.sudo.log"
check "board: factory mode button prepared" "[ -f $B1/wm-screen-backup/board_mode ] && grep -q sudoers $B1/.sudo.log"
check "board: KlipperScreen service enabled and started" "[ -e $B1/.svc/KlipperScreen.enabled ] && [ -e $B1/.svc/KlipperScreen.active ]"
check "board: --status runs" "WM_HOME=$B1 WM_INSTALLER_TEST=1 bash $SB --status | grep -q 'Mode: KlipperScreen'"
sb "$B1" --factory-restore > "$T/b1r.out"
check "restore: factory services back (enabled)" "[ -e $B1/.svc/makerbase-client.enabled ] && [ -e $B1/.svc/klipper.enabled ] && [ -e $B1/.svc/nginx.enabled ]"
check "restore: KlipperScreen gone" "[ ! -d $B1/KlipperScreen ] && [ ! -e $B1/.svc/KlipperScreen.enabled ] && [ ! -f $B1/wm-screen-backup/board_mode ]"
check "restore: reboots" "grep -q 'systemctl reboot' $B1/.sudo.log"
check "restore: list archived" "ls $B1/wm-screen-backup/disabled.list.restored-* >/dev/null"
B2="$T/b2"; mkdir -p "$B2"
check "board: never contacts the Pi (no Pi check in the script)" "! grep -q 'pi_ok\|klippy_connected' $SB"
check "board: refuses while printing" "! WM_TEST_PRINTING=1 WM_TEST_SERVICES='klipper' WM_HOME=$B2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local"
check "board: refuses when apt is broken" "! WM_TEST_APT_OK=0 WM_TEST_SERVICES='klipper' WM_HOME=$B2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local"
check "board: temporary swap added when RAM is small, none when RAM is big" "grep -q wm-tmp-swap $B1/.sudo.log && WM_TEST_MEM_MB=2000 WM_TEST_SERVICES=klipper WM_HOME=$T/b7 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi x >/dev/null 2>&1; ! grep -q wm-tmp-swap $T/b7/.sudo.log"
check "board install: the board user gets sudo without a password (default yes, recorded in test mode)" "grep -q '\[test\] sudoers nopasswd t13dp' $B1/.sudo.log"
check "board install (item 35): a user outside the sudo group is added automatically, no question" "O=\$(WM_TEST_IN_SUDO_GROUP=0 WM_TEST_SERVICES=klipper WM_HOME=$T/b10 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local --no-reboot 2>&1 </dev/null); echo \"\$O\" | grep -q 'added to the sudo group' && grep -q 'usermod -aG sudo t13dp' $T/b10/.sudo.log"
check "board install (item 35): a user already in the sudo group runs nothing" "WM_TEST_IN_SUDO_GROUP=1 WM_TEST_SERVICES=klipper WM_HOME=$T/b11 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local --no-reboot >/dev/null 2>&1 </dev/null; ! grep -q 'usermod' $T/b11/.sudo.log"
check "board install (item 35): dry run only says it would add the user" "O=\$(WM_TEST_IN_SUDO_GROUP=0 WM_TEST_SERVICES=klipper WM_HOME=$T/b12 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local --dry-run 2>&1 </dev/null); echo \"\$O\" | grep -q 'would add t13dp to the sudo group' && ! grep -q 'usermod' $T/b12/.sudo.log 2>/dev/null"
check "board install: --no-sudo-rule skips it and says so" "O=\$(WM_TEST_SERVICES=klipper WM_HOME=$T/b8 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local --no-sudo-rule --no-reboot 2>&1 </dev/null); echo \"\$O\" | grep -q 'sudo without a password skipped' && ! grep -q 'sudoers nopasswd' $T/b8/.sudo.log"
check "board install: dry run only says what it would do for the sudo rule" "WM_TEST_SERVICES=klipper WM_HOME=$T/b9 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi wmpi.local --dry-run 2>&1 </dev/null | grep -q 'would let t13dp use sudo without a password'"
check "board: Factory mode / --factory-restore removes the sudo rule again, and it only ever names the board user" "grep -q 'rm -f /etc/sudoers.d/wm-factory-restore .*SUDO_NOPASSWD_FILE' $SB && grep -q 'printf .%s ALL=(ALL) NOPASSWD: ALL.*WM_USER' $SB"
check "board: --set-pi rewrites the address and restarts KlipperScreen" "mkdir -p $T/b8/printer_data/config && printf '[printer wmpi]\nmoonraker_host: old.local\n' > $T/b8/printer_data/config/KlipperScreen.conf && WM_HOME=$T/b8 WM_INSTALLER_TEST=1 bash $SB --set-pi 192.0.2.7 >/dev/null 2>&1 && grep -q 'moonraker_host: 192.0.2.7' $T/b8/printer_data/config/KlipperScreen.conf && grep -q 'restart KlipperScreen' $T/b8/.sudo.log"
check "board: --set-pi refuses a bad address" "! WM_HOME=$T/b8 WM_INSTALLER_TEST=1 bash $SB --set-pi 'a b;rm' >/dev/null 2>&1"
ZC_T="$(mktemp -d)"; mkdir -p "$ZC_T/panels"; printf 'self.z_offset = float(self.probe["z_offset"])\n' > "$ZC_T/panels/zcalibrate.py"
sed -n '/^patch_ks_zcalibrate() {/,/^}/p' "$ROOT/scripts/screen_board.sh" > "$ZC_T/fn.sh"
check "board: Z calibrate page no longer stops when [probe] has no z_offset line" "KS_DIR=$ZC_T; . $ZC_T/fn.sh; patch_ks_zcalibrate; patch_ks_zcalibrate; grep -q 'probe.get(\"z_offset\", 0.0)' $ZC_T/panels/zcalibrate.py && [ -f $ZC_T/panels/zcalibrate.py.wm-orig ]"
check "board: Wi-Fi panel replaces the stock Network panel (wpa_cli, no NetworkManager)" "grep -q wifi_panel.py $SB && grep -q wpa_cli $ROOT/zr_tools/wifi_panel.py && ! grep -q sdbus $ROOT/zr_tools/wifi_panel.py"
check "board: with no --pi and no terminal it stops and asks for the Pi address" "! WM_HOME=$B2 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --dry-run >$T/nopi.out 2>&1 </dev/null && grep -q 'no Pi address' $T/nopi.out"
check "board: Pi address and Wi-Fi pages are installed and in the menus" "grep -q pi_address_panel.py $SB && grep -q 'menu __splashscreen pi_address' $SB && grep -q 'menu __main more pi_address' $SB"
B3="$T/b3"; mkdir -p "$B3/printer_data/config"
WM_TEST_KS_OK=fbdev sb "$B3" --pi 10.0.0.5 > "$T/b3.out"
check "board: X falls back to fbdev when modesetting does not start" "[ -e $B3/.fbdev ] && grep -q 'fbdev' $T/b3.out"
B4="$T/b4"; mkdir -p "$B4/printer_data/config"; sb "$B4" --pi wmpi.local --dry-run > "$T/b4.out"
check "board: dry run changes nothing" "[ ! -d $B4/KlipperScreen ] && [ ! -s $B4/.sudo.log ] && grep -q 'would run' $T/b4.out"
B5="$T/b5"; mkdir -p "$B5/printer_data/config"; sb "$B5" --pi wmpi.local >/dev/null; printf 'y\n' | WM_HOME="$B5" WM_INSTALLER_TEST=1 bash "$SB" --uninstall-klipperscreen > "$T/b5u.out" 2>&1
check "board uninstall-klipperscreen: removes it AND re-enables the factory services" "[ ! -d $B5/KlipperScreen ] && [ -e $B5/.svc/makerbase-client.enabled ] && [ -e $B5/.svc/klipper.enabled ] && [ -e $B5/.svc/moonraker.enabled ]"

sec "== screen rescue tool (window after 3 failed starts, USB flag)"
RS="$ROOT/screen_rescue/wm-screen-rescue"
check "rescue: scripts have valid syntax" "bash -n $RS && python3 -m py_compile $ROOT/screen_rescue/wm-rescue-window.py; rm -rf $ROOT/screen_rescue/__pycache__"
check "rescue: KlipperScreen unit stops retrying after 3 starts in 2 minutes and opens the rescue window" "grep -q 'StartLimitIntervalSec=120' $SB && grep -q 'StartLimitBurst=3' $SB && grep -q 'OnFailure=wm-screen-rescue.service' $SB"
check "rescue: the rescue unit replaces KlipperScreen (Conflicts)" "grep -q 'Conflicts=KlipperScreen.service' $SB"
RB="$T/rb"; mkdir -p "$RB/home/wm-screen-backup" "$RB/home/printer_data/config" "$RB/usb"
touch "$RB/wm-factory-restore"; chmod +x "$RB/wm-factory-restore"
# The whole output is collected first and only then printed. Otherwise "rs ... | grep -q" lets grep exit at its first match, the rescue script
# gets SIGPIPE on its next echo and dies before it writes its log line: the test then failed now and then (a race, not a fault in the script).
rs() { local o rc; o="$(WM_FACTORY_BIN="${FB:-$RB/wm-factory-restore}" WM_HOME="$RB/home" WM_RESCUE_LOG="$RB/log" WM_RESCUE_DRY=1 WM_RESCUE_TEST=1 WM_RESCUE_REASON_FILE="$RB/reason" WM_RESCUE_MEDIA_DIR="$RB/usb" bash "$RS" "$@" 2>&1)"; rc=$?; printf '%s\n' "$o"; return $rc; }
printf '[printer wmpi]\nmoonraker_host: 192.0.2.50\n' > "$RB/home/printer_data/config/KlipperScreen.conf"
touch "$RB/usb/WM-FACTORY"; rs usb-check >/dev/null
check "rescue usb: in factory mode (KlipperScreen not installed) the stick is ignored" "[ -f $RB/usb/WM-FACTORY ] && ! grep -q 'USB: WM' $RB/log"
echo "KlipperScreen on screen board" > "$RB/home/wm-screen-backup/board_mode"
rs usb-check >/dev/null
check "rescue usb: WM-FACTORY without a saved service list still restores (built-in list), flag renamed, reason written to the stick" "[ -f $RB/usb/WM-FACTORY.done ] && grep -q 'built-in list' $RB/usb/WM-RESCUE-LOG.txt && grep -q 'starting the factory restore' $RB/log"
rm -f "$RB/usb/"*; echo "makerbase-client enabled active" > "$RB/home/wm-screen-backup/disabled.list"; touch "$RB/usb/wm-factory"
rs usb-check >/dev/null
check "rescue usb: WM-FACTORY (any letter case) with a saved list starts the restore, renames the flag, writes a log, saves the settings" "[ -f $RB/usb/wm-factory.done ] && grep -q 'factory restore starts now' $RB/usb/WM-RESCUE-LOG.txt && grep -q 'starting the factory restore' $RB/log && grep -q 'factory-restore --yes --detach' $RB/log && ls $RB/home/wm-screen-backup/rescue-snapshots/*/KlipperScreen.conf >/dev/null"
rm -f "$RB/usb/"*; touch "$RB/usb/WM-RESCUE"; rs usb-check >/dev/null
check "rescue usb: WM-RESCUE opens the window (reason usb) and is renamed" "[ -f $RB/usb/WM-RESCUE.done ] && grep -q 'systemctl start --no-block wm-screen-rescue.service' $RB/log && [ \"\$(cat $RB/reason)\" = usb ]"
rm -f "$RB/usb/"* "$RB/log"; touch "$RB/usb/readme.txt"; rs usb-check >/dev/null
check "rescue usb: a stick without a flag does nothing" "[ ! -s $RB/log ] || ! grep -q 'USB: starting\|USB: opening' $RB/log"
check "rescue act: factory restore without the restore script restores the 8 factory services itself" "rm -f $RB/home/wm-screen-backup/disabled.list; FB=/nonexistent rs act factory > $T/rsf.out; for u in makerbase-client moonraker nginx klipper-mcu crowsnest makerbase-webcam; do grep -q \"systemctl enable \$u\" $RB/log || exit 1; done; ! grep -q 'systemctl enable klipper\$' $RB/log && ! grep -q 'enable hostapd' $RB/log && grep -q 'systemctl reboot' $RB/log"
check "rescue: the built-in factory list is identical in the installer and in the rescue tool" "[ \"\$(sed -n '/^FACTORY_DEFAULT=/,/\"\$/p' $SB | sed 's/^FACTORY_DEFAULT=//')\" = \"\$(sed -n '/^FACTORY_DEFAULT=/,/\"\$/p' $RS | sed 's/^FACTORY_DEFAULT=//')\" ]"
BM="$T/bm"; mkdir -p "$BM/printer_data/config"; sb "$BM" --pi wmpi.local >/dev/null; rm -f "$BM/wm-screen-backup/disabled.list"; sb "$BM" --factory-restore > "$T/bm.out"
check "board restore without a saved list uses the built-in factory list and turns the services back on" "grep -q 'built-in list' $T/bm.out && [ -e $BM/.svc/makerbase-client.enabled ] && [ -e $BM/.svc/moonraker.enabled ] && [ ! -d $BM/KlipperScreen ]"
echo "makerbase-client enabled active" > "$RB/home/wm-screen-backup/disabled.list"
check "rescue act: factory restore keeps the Pi address first and runs the detached restore" "rs act factory | grep -q 'Pi address: 192.0.2.50' && grep -q 'wm-factory-restore --factory-restore --yes --detach' $RB/log"
check "rescue act: restart clears the failed state and starts KlipperScreen" "rs act restart-ks >/dev/null; grep -q 'systemctl reset-failed KlipperScreen' $RB/log && grep -q 'systemctl start KlipperScreen' $RB/log"
check "rescue act: reset settings needs the saved defaults, keeps the Pi address" "rs act reset-settings | grep -q 'No saved default'; mkdir -p $RB/home/wm-screen-backup/known-good && cp $RB/home/printer_data/config/KlipperScreen.conf $RB/home/wm-screen-backup/known-good/ && rs act reset-settings | grep -q 'Pi address'"
check "rescue act: reinstall needs the saved copy" "rs act reinstall-files | grep -q 'No saved copy'"
check "rescue act: factory restore reports its steps for the progress bar" "rs act factory | grep -q '^STEP 1/4 Saving' && rs act factory | grep -q '^STEP 4/4'"
check "rescue act: reset settings and reinstall report their steps" "mkdir -p $RB/home/wm-screen-backup/known-good && cp $RB/home/printer_data/config/KlipperScreen.conf $RB/home/wm-screen-backup/known-good/ && rs act reset-settings | grep -q '^STEP 4/4 Restarting' && rs act reinstall-files | grep -q '^STEP 1/4 Checking'"
check "rescue window: every action asks first, and the long ones show a progress bar" "W=$ROOT/screen_rescue/wm-rescue-window.py; for a in 'restart-ks' 'reboot' 'factory' 'reset-settings' 'reinstall-files'; do grep -q \"\\\"\$a\\\"\" \$W || exit 1; done; grep -c 'self.ask(' \$W | grep -q '^[4-9]' && grep -q 'run_with_progress(\"factory\"' \$W && grep -q 'run_with_progress(\"reset-settings\"' \$W && grep -q 'run_with_progress(\"reinstall-files\"' \$W && grep -q 'Gtk.ProgressBar' \$W"
check "rescue: snapshots are handed to the board user" "grep -q 'chown -R \"\$WM_USER:\" \"\$SNAP\"' $ROOT/screen_rescue/wm-screen-rescue"
check "rescue act: reason texts" "rs act reason manual | grep -q 'by hand' && rs act reason usb | grep -q WM-RESCUE && rs act reason failed | grep -q '3 times'"
check "rescue: manual open writes the reason and starts the window" "rs open >/dev/null; grep -q manual $RB/reason && grep -q 'wm-screen-rescue.service' $RB/log"
BR="$T/br"; mkdir -p "$BR/printer_data/config"; sb "$BR" --pi wmpi.local > "$T/br.out"
F="$ROOT/usb_flags"
check "usb_flags folder: both flag files empty, each zip holds exactly one file, README links it" "[ -e $F/WM-FACTORY ] && [ ! -s $F/WM-FACTORY ] && [ -e $F/WM-RESCUE ] && [ ! -s $F/WM-RESCUE ] && [ \"\$(unzip -Z1 $F/wm-factory-flag.zip)\" = WM-FACTORY ] && [ \"\$(unzip -Z1 $F/wm-rescue-flag.zip)\" = WM-RESCUE ] && grep -q '(usb_flags/)' $ROOT/README.md"
BX="$T/bx"; mkdir -p "$BX/printer_data/config"; sb "$BX" --pi wmpi.local --no-reboot > "$T/bx.out"
check "board install: reboots at the end, unless --no-reboot" "grep -q 'systemctl reboot' $BR/.sudo.log && ! grep -q 'systemctl reboot' $BX/.sudo.log"
check "board install: rescue tool installed (defaults saved, program copy, units)" "grep -q 'rescue tool' $BR/.sudo.log && [ -f $BR/wm-screen-backup/known-good/KlipperScreen.conf ] && [ -s $BR/wm-screen-backup/ks-program.tar.gz ]"
check "board --status shows the rescue tool" "WM_HOME=$BR WM_INSTALLER_TEST=1 bash $SB --status | grep -q 'Rescue tool: installed'"
sb "$BR" --factory-restore >/dev/null
check "board restore removes the rescue tool and its copies (only the backup list stays archived)" "grep -q 'remove rescue tool' $BR/.sudo.log && [ ! -d $BR/wm-screen-backup/known-good ] && [ ! -e $BR/wm-screen-backup/ks-program.tar.gz ]"
BN="$T/bn"; mkdir -p "$BN/printer_data/config"; sb "$BN" --pi wmpi.local --no-rescue > "$T/bn.out"
check "board install --no-rescue: no rescue tool" "! grep -q 'rescue tool' $BN/.sudo.log && [ ! -d $BN/wm-screen-backup/known-good ]"
check "screen mode (F-238): the board install puts the switch next to the rescue tool and the rescue files carry the USB flag and the window button" "grep -q 'screen mode switch' $BR/.sudo.log && grep -q 'WM-KLIPPERSCREEN' $ROOT/screen_rescue/wm-screen-rescue && grep -q 'Use the factory software' $ROOT/screen_rescue/wm-rescue-window.py && [ -x $ROOT/screen_rescue/wm-screen-mode ] && [ -x $ROOT/screen_rescue/wm-screen-mode-web.py ]"
check "screen mode (F-238 F-239): the sudoers entry allows exactly factory once, factory keep and reboot" "grep -q 'wm-screen-mode factory once' $ROOT/screen_rescue/wm-screen-mode.sudoers && grep -q 'wm-screen-mode factory keep' $ROOT/screen_rescue/wm-screen-mode.sudoers && grep -q 'wm-screen-mode reboot' $ROOT/screen_rescue/wm-screen-mode.sudoers && ! grep -q 'NOPASSWD: /usr/local/sbin/wm-screen-mode *$' $ROOT/screen_rescue/wm-screen-mode.sudoers"
check "screen mode (F-238): a dry factory keep stops KlipperScreen and keeps the factory choice, a dry klipperscreen starts it, nothing is removed" "MB=\$(mktemp -d); mkdir -p \$MB/wm-screen-backup; WM_HOME=\$MB WM_MODE_LOG=\$MB/log WM_MODE_DRY=1 WM_MODE_NO_DETACH=1 bash $ROOT/screen_rescue/wm-screen-mode factory keep >/dev/null; grep -q 'would run: systemctl stop KlipperScreen' \$MB/log && grep -q 'would run: systemctl disable KlipperScreen' \$MB/log && WM_HOME=\$MB WM_MODE_LOG=\$MB/log2 WM_MODE_DRY=1 WM_MODE_NO_DETACH=1 bash $ROOT/screen_rescue/wm-screen-mode klipperscreen >/dev/null; grep -q 'would run: systemctl start KlipperScreen' \$MB/log2; ! grep -q 'rm \|remove' \$MB/log \$MB/log2"
check "screen S1.3.0 (F-236 F-237 F-238 F-239 F-240 F-243): the screen files hold the banner filter, Print map, Factory software, Reboot and Shut down windows, and the ACE buttons call the macros without the old confirm" "grep -q '_ZR_KEEP_BANNER' $ROOT/zr_tools/zr_tools.py && grep -q 'Print map' $ROOT/zr_tools/zr_views.py && grep -q 'Factory software' $ROOT/zr_tools/zr_views.py && grep -q 'Reboot now' $ROOT/zr_tools/zr_views.py && grep -q 'Shut down now' $ROOT/zr_tools/zr_views.py && grep -q 'self._gcode(f\"ACE_WM_LOAD T={i}\")' $ROOT/zr_tools/zr_tools.py"
check "dock speed (F-241): both factory change_macros.cfg have the factory dock speed and the slow last 15 mm of the grab" "( for m in ultra ultra-s; do f=$ROOT/factory/\$m/config/change_macros.cfg; grep -q 'G4 P1000' \$f && grep -q 'position_y+0.4-15} F9600' \$f && grep -q 'position_y+0.4} F1000' \$f || exit 1; done )"
check "dock speed (F-241): an update leaves a change_macros.cfg that already has it alone, and a file with the old fast dock speed gets it" "MD=\$(mktemp -d); cp $ROOT/factory/ultra-s/config/*.cfg \$MD/; python3 -I $ROOT/scripts/wm_macro_patches.py \$MD >/dev/null && sed -i 's/G4 P1000/G4 P300/' \$MD/change_macros.cfg && python3 -I $ROOT/scripts/wm_macro_patches.py \$MD --write --stamp F241 >/dev/null; grep -q 'G4 P1000' \$MD/change_macros.cfg"
check "windows (F-243): WM_BED_PID, WM_RESUME_TOOL, WM_NOZZLE_GROWTH, ACE_WM_LOAD and ACE_WM_UNLOAD have their What it does windows and the internal ACE callers pass CONFIRM=1" "grep -q 'gcode_macro _WM_BEDPID_INFO' $ROOT/rpi-cfg/rpi_calibration.cfg && grep -q 'gcode_macro _WM_GROWTHSET_INFO' $ROOT/rpi-cfg/rpi_calibration.cfg && grep -q 'gcode_macro _WM_RTOOL_INFO' $ROOT/rpi-cfg/rpi_base.cfg && grep -q 'ACE_WM_UNLOAD T={t} CONFIRM=1' $ROOT/rpi-cfg/rpi_base.cfg && grep -q 'ACE_WM_LOAD T={t} CONFIRM=1' $ROOT/rpi-cfg/rpi_base.cfg"
check "rescue: the ZR Tools System page has a Rescue tile on the board" "grep -q '_sys_rescue' $ROOT/zr_tools/zr_views.py && grep -q 'sudoers' $SB"
check "2.31.0 (F-235): the screen has a Move page (home, jog, coordinates, Go to position with a number pad that stays open) instead of the Filament tab" "grep -q 'def show_move' $ROOT/zr_tools/zr_views.py && grep -q 'def show_goto' $ROOT/zr_tools/zr_views.py && grep -q 'def _go_run' $ROOT/zr_tools/zr_views.py && grep -q '\"move\", \"Move\"' $ROOT/zr_tools/zr_tools.py && grep -q 'ZR_MOVE' $ROOT/zr_tools/zr_views.py && ! grep -A12 'def _go_run' $ROOT/zr_tools/zr_views.py | grep -q 'self.show_move()' && python3 -m py_compile $ROOT/zr_tools/zr_views.py"
B6="$T/b6"; mkdir -p "$B6/printer_data/config"; sb "$B6" --pi wmpi.local >/dev/null; sb "$B6" --pi wmpi.local >/dev/null
check "board: running twice keeps the ORIGINAL saved state" "grep -q 'makerbase-client enabled active' $B6/wm-screen-backup/disabled.list"

sec "== screen board pre-check (runs on the Mac)"
PC="$ROOT/scripts/screen_board_precheck.sh"; mkdir -p "$T/pc"
check "precheck syntax" "bash -n $PC"
check "precheck reads package and service lists from screen_board.sh" "(cd $T/pc && bash $PC --local-test | grep -q SUMMARY)"
check "precheck writes a scrubbed report" "ls $T/pc/screen_board_precheck_*.txt >/dev/null && ! grep -q TM88888 $T/pc/screen_board_precheck_*.txt"
check "precheck is read-only (no sudo, no service changes in its code)" "! grep -E 'systemctl (stop|start|disable|enable|restart)|apt-get (install|upgrade|remove)[^|]*[^s] ' $PC | grep -v -E '^[[:space:]]*#|-s install|Still to do|sudo systemctl' | grep -q ."
check "precheck needs a board address" "! bash $PC"
sec "== Mac preflight script"
PF="$ROOT/scripts/screen_board_preflight_mac.sh"
check "preflight syntax" "bash -n $PF"
check "preflight needs the board address" "! bash $PF"
WM_REPORT="$T/pf2.txt" bash "$PF" --local-test > "$T/pf2.out" 2>&1
check "preflight has no Pi checks" "! grep -qi 'Pi Moonraker\\|Pi checks' $T/pf2.out"
WM_REPORT="$T/pf3.txt" bash "$PF" --local-test --pi 127.0.0.1 > "$T/pf3.out" 2>&1
WM_REPORT="$T/pf.txt" bash "$PF" --local-test --pi 127.0.0.1 > "$T/pf.out" 2>&1; PFRC=$?
check "preflight runs all sections and gives a verdict" "grep -q 'On the screen board' $T/pf.out && grep -q 'Verdict' $T/pf.out && [ -s $T/pf.txt ]"
check "preflight says NOT READY on a machine that is not the board" "[ $PFRC = 1 ] && grep -q 'NOT READY' $T/pf.out"
remote_part() { awk '/read -r -d .. REMOTE/{f=1} f{print} /^RSH/{f=0}' "$PF" | grep -v 'apt-get -s'; }
check "preflight read-only part has no write/install commands" "! remote_part | grep -E 'apt-get (install|upgrade)|rm -rf|systemctl (stop|disable|start|enable)|dpkg -i'"
check "preflight read-only part is not empty" "[ \$(remote_part | wc -l) -gt 50 ]"

# --- Klippain Shake&Tune add-on and remote-access questions removed from the install ---
mkstage "$T/stage_hk"; HK="$T/hk"; mkdir -p "$HK"; inst "$HK" --from-stage "$T/stage_hk" --screen off >/dev/null
check "--shaketune needs on or off" "! bash $ROOT/installer.sh --shaketune maybe"
check "--help mentions --shaketune" "bash $ROOT/installer.sh --help | grep -q shaketune"
check "shaketune is pinned" "grep -q '^shaketune|https://github.com/Frix-x/klippain-shaketune|[0-9a-f]\\{40\\}' $ROOT/config/pins/addons.txt"
printf "[server]\n" > "$HK/printer_data/config/moonraker.conf"; : > "$HK/.sudo.log"
printf '\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# DO NOT EDIT THIS BLOCK OR BELOW.\n' >> "$HK/printer_data/config/printer.cfg"
OUT="$(inst "$HK" --update --shaketune on)"
check "--shaketune on installs the extension link and config" "[ -L $HK/klipper/klippy/extras/shaketune ] && [ -f $HK/printer_data/config/shaketune.cfg ]"
check "--shaketune on adds include and update manager, with a printer.cfg copy" "grep -q 'include shaketune.cfg' $HK/printer_data/config/printer.cfg && grep -q 'Klippain-ShakeTune' $HK/printer_data/config/moonraker.conf && ls $HK/printer_data/config/printer.cfg.wm-before-shaketune-* $HK/printer_data/config/backup/printer.cfg.wm-before-shaketune-* 2>/dev/null | grep -q ."
check "--shaketune on puts the include above the SAVE_CONFIG block, not under it" "grep -q SAVE_CONFIG $HK/printer_data/config/printer.cfg && ! sed -n '/SAVE_CONFIG/,\$p' $HK/printer_data/config/printer.cfg | grep -q '^\\[include'"
check "--shaketune on restarts klipper (once) at the end, because it was running" "[ \$(grep -c 'restart klipper' $HK/.sudo.log) -eq 1 ]"
check "--shaketune is remembered" "grep -rq 'WANT_SHAKETUNE=1' $HK/wm-rpi-backup"
check "--remove shaketune removes it" "M 'y\\n' $HK --remove shaketune | grep -q 'removed' && [ ! -e $HK/klipper/klippy/extras/shaketune ] && ! grep -q 'shaketune.cfg' $HK/printer_data/config/printer.cfg"
# an include that an older installer appended under the SAVE_CONFIG block is moved back above it (and the doctor reports it)
printf '[include old_addon.cfg]\n[include shaketune.cfg]\n' >> "$HK/printer_data/config/printer.cfg"
check "the doctor reports an include under the SAVE_CONFIG block" "M 'n\\n' $HK --doctor | grep -qi 'include.*under the SAVE_CONFIG'"
inst "$HK" --update --shaketune on >/dev/null
check "--update moves a stray include from under the SAVE_CONFIG block to above it, with a copy" "! sed -n '/SAVE_CONFIG/,\$p' $HK/printer_data/config/printer.cfg | grep -q '^\\[include' && grep -q 'include old_addon.cfg' $HK/printer_data/config/printer.cfg && [ \$(grep -c 'include shaketune.cfg' $HK/printer_data/config/printer.cfg) -eq 1 ] && ls $HK/printer_data/config/printer.cfg.wm-before-include-fix-* $HK/printer_data/config/backup/printer.cfg.wm-before-include-fix-* 2>/dev/null | grep -q ."
OUT="$(inst "$T/hq" --dry-run --from-stage "$T/stage_hk" --model ultra-s --screen off)"
check "the plan shows Shake&Tune" "echo \"\$OUT\" | grep -qi 'shake&tune'"
check "the install does not ask about Obico, OctoApp or OctoEverywhere" "! M '\\n\\n\\n\\n\\n' $T/hq2 --dry-run | grep -qi 'Do you want.*\\(obico\\|octoapp\\|octoeverywhere\\)'"

# --- empty canbus_uuid (factory files) must not cause "Duplicate canbus_uuid" ---
mkstage "$T/stage_cu"; CUU="$T/cuu"; mkdir -p "$CUU"; inst "$CUU" --from-stage "$T/stage_cu" --screen off >/dev/null
for n in 0 1 2 3; do printf '[mcu T%s]\ncanbus_uuid:%s\n' $n "$([ $n = 1 ] && echo ' ')" > "$CUU/printer_data/config/wm_zru_thr$n.cfg"; done
printf '[mcu CELL]\ncanbus_uuid:\n' > "$CUU/printer_data/config/wm_zru_load_cell.cfg"
printf '[mcu]\ncanbus_uuid: aa0000000000\n' > "$CUU/printer_data/config/wm_zru_mcu.cfg"
M '\n' $CUU --first-start >/dev/null 2>&1
dups() { cat $CUU/printer_data/config/wm_zru_*.cfg | grep -i canbus_uuid | sed 's/ //g' | sort | uniq -d; }
check "empty canbus_uuid in T0-T3 and the load cell get unique placeholders" "[ -z \"\$(dups)\" ] && grep -q 'canbus_uuid: b20000000000' $CUU/printer_data/config/wm_zru_thr2.cfg && grep -q 'canbus_uuid: b40000000000' $CUU/printer_data/config/wm_zru_load_cell.cfg"
check "the old files are kept" "ls $CUU/wm-rpi-backup/uuid-*/wm_zru_thr0.cfg"
check "a real uuid is never overwritten" "grep -q 'aa0000000000' $CUU/printer_data/config/wm_zru_mcu.cfg"

# --- add-on install from the menu touches only that add-on ---
OA="$T/oa"; mkdir -p "$OA"; inst "$OA" --from-stage "$T/stage_hk" --screen off >/dev/null; : > "$OA/.sudo.log"
OUT="$(inst "$OA" --update --only-addon shaketune --shaketune on)"
check "add-on only: Shake&Tune is installed" "[ -L $OA/klipper/klippy/extras/shaketune ]"
check "Shake&Tune: a detached copy is put on branch main at the same commit, files unchanged (Moonraker showed it INVALID)" "python3 $ROOT/tests/test_shaketune_branch.py"
check "add-on only: no system packages, nginx, can0 rule or panel work" "! grep -E 'nginx|can0|python3-|klippy-requirements' $OA/.sudo.log"
check "add-on only says so" "echo \"\$OUT\" | grep -q 'Only this add-on'"
check "full update still updates everything" "inst $OA --update | grep -q 'Updated: services, nginx'"

# --- backup before update, Status, Network and system, Spoolman ---
sec "== 1.15.1 fixes"
HR="$G1"; mkdir -p "$HR/crowsnest"
OUT="$(inst "$HR" --doctor)"
check "doctor: no camera means the webcam service waits, not a problem" "echo \"$OUT\" | grep -q 'waiting for a camera'"
OUT="$(WM_TEST_CAMERA=1 inst "$HR" --doctor)"
check "doctor: camera plugged in but service not running is a problem" "echo \"$OUT\" | grep -q 'camera is plugged in but the webcam service is not running'"
check "status: webcam row says waiting for a camera" "inst $HR --status | grep -q 'waiting for a camera'"
check "menu: Add-ons, Webcam (installed) offers setting up the cameras again" "M '3\n1\n0\n0\n0\n' $HR --menu | grep -q 'Set up the cameras again'"
check "menu: Check and fix has Fix everything" "M '4\n0\n0\n' $HR --menu | grep -q 'Fix everything'"
check "--doctor --fix-all explains and asks once" "inst $HR --doctor --fix-all | grep -q 'Fix everything: every problem'"
check "hostname: /etc/hosts is changed before hostnamectl" "awk '/^do_set_hostname/,/^}/' $ROOT/installer.sh | grep -n 'sed -i\|hostnamectl' | head -2 | head -1 | grep -q 'sed -i'"
check "klipper wait stops early on error" "grep -qF -e '-ge 2' $ROOT/installer.sh"
check "system files are removed quietly" "grep -q 'not loaded' $ROOT/installer.sh"
check "info line mentions Spoolman" "grep -q 'Shake&Tune and Spoolman are not part' $ROOT/installer.sh"

sec "== backup before update / status / system page / Spoolman"
mkstage "$T/stage_ns"; NS="$T/ns"; mkdir -p "$NS"; inst "$NS" --from-stage "$T/stage_ns" --screen off >/dev/null
printf "[server]\n" > "$NS/printer_data/config/moonraker.conf"; printf "klippy_apis/printer/restart\nSpoolman_x\n" > "$NS/printer_data/moonraker.asvc"
inst "$NS" --update >/dev/null
check "--update saves a backup first" "ls $NS/ultra-backup/settings/wm-backup-*-before-update-*.tgz"
check "the backup holds the config" "tar tzf \$(ls $NS/ultra-backup/settings/*before-update*.tgz | head -1) | grep -q printer_data/config/printer.cfg"
check "the backup before an update holds TM_T1/factory_settings" "tar tzf \$(ls $NS/ultra-backup/settings/*before-update*.tgz | head -1) | grep -q TM_T1/factory_settings"
for i in 1 2 3 4 5 6 7; do touch -d "2020-01-0$i" "$NS/ultra-backup/settings/wm-backup-ultra-s-before-update-2020010$i.tgz"; done
inst "$NS" --update >/dev/null
check "only the newest 5 automatic backups are kept" "[ \$(ls $NS/ultra-backup/settings/*before-update*.tgz | wc -l) -le 5 ]"
rm -f $NS/ultra-backup/settings/*; inst "$NS" --update --no-backup >/dev/null
check "--no-backup skips it" "[ -z \"\$(ls $NS/ultra-backup/settings 2>/dev/null)\" ]"
inst "$NS" --update --only-addon shaketune --shaketune on >/dev/null
check "an add-on install saves a backup too" "ls $NS/ultra-backup/settings/*before-update*.tgz"
OUT="$(inst "$NS" --status)"
check "--status shows services, add-ons and CAN ids" "echo \"$OUT\" | grep -q 'Status (changes nothing)' && echo \"$OUT\" | grep -q 'Add-ons:' && echo \"$OUT\" | grep -q 'CAN ids in the config' && echo \"$OUT\" | grep -q 'spoolman'"
check "--status changes nothing" "[ -z \"\$(ls $NS/wm-install-logs 2>/dev/null)\" ]"
check "--system-info shows host name and time zone" "inst $NS --system-info | grep -q 'Host name' && inst $NS --system-info | grep -q 'Time zone'"
check "--set-hostname refuses a bad name" "! inst $NS --set-hostname 'Bad Name!'"
: > "$NS/.sudo.log"; M 'n\n' $NS --set-hostname newname >/dev/null; check "--set-hostname asks first (default no)" "! grep -q hostnamectl $NS/.sudo.log"
M 'y\n' $NS --set-hostname newname >/dev/null; check "--set-hostname changes it after yes" "grep -q 'hostnamectl set-hostname newname' $NS/.sudo.log"
M 'y\n' $NS --set-timezone America/Toronto >/dev/null; check "--set-timezone changes it after yes" "grep -q 'timedatectl set-timezone America/Toronto' $NS/.sudo.log"
check "menu: Check and fix has Status, Advanced has Network and system, Add-ons has Spoolman" "M '4\n0\n0\n' $NS --menu | grep -q 'Status' && M '7\n0\n0\n' $NS --menu | grep -q 'Network and system' && M '3\n0\n0\n' $NS --menu | grep -q 'Spoolman'"
check "--help mentions the new options" "bash $ROOT/installer.sh --help | grep -q -- '--spoolman' && bash $ROOT/installer.sh --help | grep -q -- '--status' && bash $ROOT/installer.sh --help | grep -q -- '--set-timezone'"
check "--spoolman needs on or off" "! bash $ROOT/installer.sh --spoolman maybe"
inst "$NS" --update --only-addon spoolman --spoolman on >/dev/null
check "Spoolman: folder, service step, [spoolman] and update entry, service name in asvc" "[ -d $NS/Spoolman ] && grep -q '^\[spoolman\]' $NS/printer_data/config/moonraker.conf && grep -q 'update_manager Spoolman' $NS/printer_data/config/moonraker.conf && grep -qx Spoolman $NS/printer_data/moonraker.asvc && grep -q 'spoolman install.sh' $NS/.sudo.log"
check "Spoolman is remembered and shown in the plan" "grep -q 'WANT_SPOOLMAN=1' $NS/wm-rpi-backup/install.conf && inst $NS --dry-run --update | grep -qi spoolman"
mkdir -p "$NS/.local/share/spoolman"; echo db > "$NS/.local/share/spoolman/spoolman.db"
check "--remove spoolman asks first and keeps everything on no" "M 'n\n' $NS --remove spoolman | grep -q 'Nothing changed' && [ -d $NS/Spoolman ]"
check "--remove spoolman removes it, drops its config sections, keeps the database" "M 'y\nn\n' $NS --remove spoolman | grep -q 'Spoolman removed' && [ ! -e $NS/Spoolman ] && ! grep -q 'spoolman' $NS/printer_data/config/moonraker.conf && ! grep -qx Spoolman $NS/printer_data/moonraker.asvc && [ -f $NS/.local/share/spoolman/spoolman.db ]"

sec "== Pi model, tty group, board temperatures and the host MCU"
PS="$T/ps"; rm -rf "$PS"; mkdir -p "$PS/printer_data/config" "$PS/.svc" "$PS/klipper/klippy/extras"; touch "$PS/.svc/klipper.active" "$PS/.svc/klipper-mcu.active"
for m in "" " HUB" " EX_T" " T0" " T1" " CELL"; do printf '[mcu%s]\nserial: x\n' "$m" > "$PS/printer_data/config/b${m// /_}.cfg"; done
printf '[mcu rpi]\nserial: /tmp/x\n' > "$PS/printer_data/config/zz_old.cfg.bak"
printf '[include b.cfg]\n[include b_HUB.cfg]\n\n[save_variables]\nfilename: /tmp/v.cfg\n\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# DO NOT EDIT THIS BLOCK OR BELOW.\n' > "$PS/printer_data/config/printer.cfg"
: > "$PS/.sudo.log"; OUT="$(inst "$PS" --pi-sensors)"; PC="$PS/printer_data/config"
check "--pi-sensors writes one temperature sensor for every [mcu] board and names them (part board-temps of rpi_pi.cfg)" "python3 $ROOT/scripts/wm_rpi_pi.py has $PC board-temps && grep -q '^\[temperature_sensor mcu_main\]' $PC/rpi_pi.cfg && grep -q 'sensor_mcu: HUB' $PC/rpi_pi.cfg && grep -q '^\[temperature_sensor mcu_extruder\]' $PC/rpi_pi.cfg && grep -q '^\[temperature_sensor mcu_t0\]' $PC/rpi_pi.cfg && grep -q '^\[temperature_sensor mcu_loadcell\]' $PC/rpi_pi.cfg && [ ! -e $PC/rpi_mcu_temps.cfg ]"
check "board temperature sensors use sensor_mcu with the right board and a wide range" "grep -c 'min_temp: -20' $PC/rpi_pi.cfg | grep -qx 6 && grep -c 'max_temp: 110' $PC/rpi_pi.cfg | grep -qx 6 && ! grep -q 'sensor_mcu: rpi' $PC/rpi_pi.cfg"
check "rpi_pi.cfg is included once, above the SAVE_CONFIG block" "[ \$(grep -c '^\[include rpi_pi.cfg\]' $PC/printer.cfg) = 1 ] && awk '/^\[include rpi_pi.cfg\]/{a=NR} /SAVE_CONFIG/{s=NR} END{exit !(a<s)}' $PC/printer.cfg"

# 2.35.0: the one-update-at-a-time lock (2.37.0: wm_my_overrides.cfg is gone, see section 74)
HO="$T/ovr"; mkdir -p "$HO/printer_data/config"
printf '[include a.cfg]\n\n[include shaketune.cfg]\n\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# DO NOT EDIT THIS BLOCK OR BELOW.\n#*#\n#*# [stepper_x]\n#*# position_endstop = 1\n' > "$HO/printer_data/config/printer.cfg"
( flock 7; sleep 8 ) 7>"$T/upd.lock" & sleep 1
WM_UPDATE_LOCKFILE="$T/upd.lock" WM_UPDATE_LOCK_WAIT=2 WM_TEST_NO_BOARD_UPDATE=1 inst "$HO" --update-boards > "$T/lock1.out"; wait
check "a second update waits for the running one and stops with a clear message when it does not finish" "grep -q 'Another update is running' $T/lock1.out && grep -q 'did not finish in time' $T/lock1.out"
WM_UPDATE_LOCKFILE="$T/upd.lock" WM_TEST_NO_BOARD_UPDATE=1 inst "$HO" --update-boards > "$T/lock2.out"
check "with no other update running the lock is taken without waiting" "! grep -q 'Another update is running' $T/lock2.out && grep -q 'the boards are not updated now' $T/lock2.out"
check "the Fluidd update script tells the installer it already holds the lock" "grep -q 'export WM_UPDATE_LOCK_HELD=1' $ROOT/scripts/pi_update.sh"
check "the backup before an update accepts tar exit 1 (a file changed while it was read) and names tar's reason when it fails" "grep -q 'trc\" -le 1' $ROOT/installer.sh && grep -q 'tar said:' $ROOT/installer.sh"
check "a board whose screen is current but whose release mark is behind gets only the mark (nothing restarts)" "grep -q 'release mark set to' $ROOT/installer.sh"
check "[mcu rpi] is the part host-mcu of rpi_pi.cfg, with the host MCU socket" "python3 $ROOT/scripts/wm_rpi_pi.py has $PC host-mcu && grep -q '^\[mcu rpi\]' $PC/rpi_pi.cfg && grep -q 'serial: /tmp/klipper_host_mcu' $PC/rpi_pi.cfg && [ ! -e $PC/rpi_mcu.cfg ]"
check "Klipper is restarted once for each, and a copy of printer.cfg is kept" "[ \$(grep -c 'systemctl restart klipper' $PS/.sudo.log) = 2 ] && ls $PC/printer.cfg.wm-before-board-temps-* $PC/printer.cfg.wm-before-host-mcu-*"
check "a second run changes nothing" "OUT2=\$(inst $PS --pi-sensors); echo \"\$OUT2\" | grep -q 'already in use' && [ \$(grep -c 'include rpi_pi.cfg' $PC/printer.cfg) = 1 ] && [ \$(grep -c '^\[mcu rpi\]' $PC/rpi_pi.cfg) = 1 ]"
PR="$T/pr"; rm -rf "$PR"; cp -a "$PS" "$PR"; rm -f "$PR/printer_data/config/rpi_"*.cfg "$PR/printer_data/config/"printer.cfg.wm-*; sed -i '/include rpi_/d' "$PR/printer_data/config/printer.cfg"; : > "$PR/.sudo.log"; cp "$PR/printer_data/config/printer.cfg" "$T/pr.before"
OUT="$(WM_TEST_KLIPPER_AFTER=error inst "$PR" --pi-sensors)"
check "when Klipper does not become ready the sensors are taken out again, printer.cfg is back as it was, and it says so" "echo \"\$OUT\" | grep -q 'Taking it out again' && cmp -s $T/pr.before $PR/printer_data/config/printer.cfg && ! python3 $ROOT/scripts/wm_rpi_pi.py has $PR/printer_data/config board-temps && echo \"\$OUT\" | grep -q 'was not added'"
check "...and Klipper is restarted a second time to load the old config" "[ \$(grep -c 'systemctl restart klipper' $PR/.sudo.log) -ge 2 ]"
PN="$T/pn"; rm -rf "$PN"; cp -a "$PS" "$PN"; rm -f "$PN/.svc/klipper.active"; rm -f "$PN/printer_data/config/rpi_"*.cfg; sed -i '/include rpi_/d' "$PN/printer_data/config/printer.cfg"; : > "$PN/.sudo.log"
OUT="$(inst "$PN" --pi-sensors)"
check "Klipper not running: nothing is changed and it says when to run it" "echo \"\$OUT\" | grep -q 'Klipper is not running' && ! python3 $ROOT/scripts/wm_rpi_pi.py has $PN/printer_data/config board-temps && ! grep -q 'restart klipper' $PN/.sudo.log"
PP="$T/pp"; rm -rf "$PP"; cp -a "$PN" "$PP"; touch "$PP/.svc/klipper.active"
OUT="$(WM_TEST_PRINT_STATE=printing inst "$PP" --pi-sensors)"; RCP=$?
check "during a print --pi-sensors refuses" "[ $RCP != 0 ] && ! python3 $ROOT/scripts/wm_rpi_pi.py has $PP/printer_data/config board-temps"
check "--dry-run changes nothing" "inst $PN --dry-run --pi-sensors | grep -q 'would add' ; ! python3 $ROOT/scripts/wm_rpi_pi.py has $PN/printer_data/config board-temps"
PF="$T/pf"; rm -rf "$PF"; mkdir -p "$PF"; OUT="$(WM_TEST_PI_SENSORS_FLOW=1 WM_TEST_CANQUERY=$T/can_ok.txt inst "$PF" --from-github --model ultra-s)"
check "an install runs the sensors step at the end, after Klipper is started, and includes the Pi sensor" "echo \"\$OUT\" | grep -q 'Board temperatures and the host MCU' && python3 $ROOT/scripts/wm_rpi_pi.py has $PF/printer_data/config board-temps && ! python3 $ROOT/scripts/wm_rpi_pi.py has $PF/printer_data/config host-mcu && python3 $ROOT/scripts/wm_rpi_pi.py has $PF/printer_data/config pi-temp && grep -q 'include rpi_pi.cfg' $PF/printer_data/config/printer.cfg"
check "...and [mcu rpi] is left out when the klipper-mcu service is not running" "echo \"\$OUT\" | grep -q 'klipper-mcu service is not running'"
check "the tty group is added with the others" "grep -q 'usermod -aG dialout,plugdev,moonraker-admin,tty' $ROOT/installer.sh"
check "rpi_pi.cfg: the Pi temperature sensor, limit 85 (config/rpi_pi_temp.cfg, part pi-temp)" "grep -q '^\[temperature_sensor raspberry_pi\]' $ROOT/config/rpi_pi_temp.cfg && grep -q 'sensor_type: temperature_host' $ROOT/config/rpi_pi_temp.cfg && grep -q 'max_temp: 85' $ROOT/config/rpi_pi_temp.cfg"
OUT="$(WM_TEST_PI_MODEL='Raspberry Pi 4 Model B Rev 1.4' inst "$PS" --status)"
check "--status shows the Pi model and memory" "echo \"\$OUT\" | grep -q 'Computer: Raspberry Pi 4 Model B Rev 1.4, 4096 MB memory'"
check "the install plan shows the Pi model" "WM_TEST_PI_MODEL='Raspberry Pi 5 Model B Rev 1.0' inst $T/pmodel5 --from-github --model ultra-s --dry-run | grep -q 'This computer:   Raspberry Pi 5 Model B Rev 1.0'"
OUT="$(WM_TEST_PI_MODEL='Raspberry Pi 3 Model B Plus Rev 1.3' WM_TEST_PI_RAM_MB=906 inst $T/pmodel3 --from-github --model ultra-s --dry-run)"
check "a Pi 3 and low memory get a warning each, and the install is not blocked" "echo \"\$OUT\" | grep -q 'This is a Raspberry Pi 3' && echo \"\$OUT\" | grep -q 'Only 906 MB of memory' && echo \"\$OUT\" | grep -q 'Plan'"
OUT="$(WM_TEST_PI_MODEL='Raspberry Pi 5 Model B Rev 1.0' inst $T/pmodel5b --from-github --model ultra-s --dry-run)"
check "a Pi 4 or 5 gets no warning" "! echo \"\$OUT\" | grep -q 'recommended'"
check "the support bundle's system report has the model line" "grep -q 'computer: \$(pi_model_line)' $ROOT/installer.sh"
check "Doctor knows the host MCU service and the tty group" "grep -q 'klipper-mcu (the host MCU)' $ROOT/installer.sh && grep -q 'is not in the tty group' $ROOT/installer.sh"
check "--help lists --pi-sensors" "bash $ROOT/installer.sh --help | grep -q -- '--pi-sensors'"
check "docs/HOST_MCU.md describes [mcu rpi], the tty group and the rollback" "grep -q 'mcu rpi' $ROOT/docs/HOST_MCU.md && grep -q 'tty' $ROOT/docs/HOST_MCU.md && grep -qi 'put back as they were' $ROOT/docs/HOST_MCU.md"

sec "== ACE Pro (install question, add-on, doctor, removal)"
STUBACE="$T/acestub"; mkdir -p "$STUBACE/extras/ace" "$STUBACE/config"; echo VERSION > /dev/null; echo 9.9.9 > "$STUBACE/VERSION"; mkdir -p "$STUBACE/.git"
cat > "$STUBACE/installer.sh" <<'STUBEOF'
#!/bin/bash
# stands in for wm-ultra-fluidd-acepro-panel's installer.sh (same options and files, no questions beyond the uninstall one)
echo "$1 home=$ACE_INSTALL_HOME test=$ACE_INSTALLER_TEST" >> "$ACE_INSTALL_HOME/.ace-stub.log"
cfg="$ACE_CONFIG_DIR"; x="$ACE_KLIPPER_DIR/klippy/extras"; here="$(cd "$(dirname "$0")" && pwd)"
case "$1" in
  --install|--update)
    for f in rpi_ace_driver rpi_ace rpi_endless rpi_stats; do echo "# $f" > "$cfg/$f.cfg"; grep -q "^\[include $f.cfg\]" "$cfg/printer.cfg" || sed -i "1i [include $f.cfg]" "$cfg/printer.cfg"; done
    echo 'VERSION="9.9.9"' > "$cfg/rpi-ultra-install.conf"; ln -sfn "$here/extras/ace" "$x/ace"; mkdir -p "$ACE_INSTALL_HOME/acepro-backup/wm-1" ;;
  --uninstall)
    read -r a; [ "$a" = y ] || exit 0
    sed -i -E '/^\[include rpi_(ace_driver|ace|endless|stats)\.cfg\]/d' "$cfg/printer.cfg"; rm -f "$cfg"/rpi_ace_driver.cfg "$cfg"/rpi_ace.cfg "$cfg"/rpi_endless.cfg "$cfg"/rpi_stats.cfg "$cfg/rpi-ultra-install.conf" "$x/ace" ;;
esac
STUBEOF
chmod +x "$STUBACE/installer.sh"; export WM_TEST_ACEPRO_SRC="$STUBACE"
check "--acepro needs on or off" "! bash $ROOT/installer.sh --acepro maybe"
check "--help mentions --acepro" "bash $ROOT/installer.sh --help | grep -q -- '--acepro'"
OUTA="$(inst "$T/hqa" --dry-run --from-stage "$T/stage_hk" --model ultra-s --screen off)"
check "the install plan lists the ACE Pro as not chosen (default no) and the install asks about it" "grep -q 'Do you have an Anycubic ACE Pro to connect' $ROOT/installer.sh && echo \"\$OUTA\" | grep -E 'ace pro +no \\(add later'"
OUTA="$(inst "$T/hqa2" --dry-run --from-stage "$T/stage_hk" --model ultra-s --screen off --acepro on)"
check "the plan says yes with --acepro on, and the step would download the project" "echo \"\$OUTA\" | grep -E 'ace pro +yes'"
check "the question is asked in the install and a yes answer is used" "printf 'y\\ny\\ny\\ny\\ny\\ny\\ny\\ny\\ny\\ny\\n' | WM_TEST_NO_FETCH=1 WM_HOME=$T/hqa3 WM_INSTALLER_TEST=1 WM_TEST_PANEL_DIR=$T/stubpanel bash $ROOT/installer.sh --dry-run --from-stage $T/stage_hk --model ultra-s --screen off --cameras 1 --cam-resolution 720p --cam-fps 15 --cam-mode ustreamer 2>&1 | grep -E 'ace pro +yes'"
check "without --acepro the ACE project is not touched" "[ ! -e $NS/wm-ultra-fluidd-acepro-panel ] && [ ! -e $NS/.ace-stub.log ]"
check "ACE Pro is not installed to start with, shown in the add-on list" "M '3\n0\n0\n' $NS --menu | grep -q 'Anycubic ACE Pro.*not installed'"
inst "$NS" --update --only-addon acepro --acepro on > "$T/ace1.out"
check "ACE Pro: the project is downloaded and its installer runs as an install, for this home, in test mode" "[ -f $NS/wm-ultra-fluidd-acepro-panel/installer.sh ] && grep -q -- '--install home=$NS test=1' $NS/.ace-stub.log"
check "ACE Pro: config files, include lines and the Klipper link are in place" "for f in rpi_ace_driver rpi_ace rpi_endless rpi_stats; do [ -f $NS/printer_data/config/\$f.cfg ] && grep -q \"^\\[include \$f.cfg\\]\" $NS/printer_data/config/printer.cfg || exit 1; done; [ -L $NS/klipper/klippy/extras/ace ]"
check "ACE Pro: remembered, in the plan, in --status" "grep -q 'WANT_ACEPRO=1' $NS/wm-rpi-backup/install.conf && inst $NS --status | grep -E 'acepro +installed'"
check "ACE Pro: the next --update runs the project's installer as an update, no second include line" "inst $NS --update --only-addon acepro >/dev/null; grep -q -- '--update home=' $NS/.ace-stub.log && [ \$(grep -c 'include rpi_ace.cfg' $NS/printer_data/config/printer.cfg) = 1 ]"
printf '[server]\nport: 7125\n\n[update_manager]\n' > "$NS/printer_data/config/moonraker.conf"
inst "$NS" --update --only-addon acepro >/dev/null; inst "$NS" --update --only-addon acepro >/dev/null
check "Fluidd update entries: the panel repo and this installer's repo are added to moonraker.conf once, other sections stay, a copy is kept" "grep -c '^\[update_manager wm-ultra-fluidd-acepro-panel\]' $NS/printer_data/config/moonraker.conf | grep -qx 1 && grep -c '^\[update_manager wm_ultra_vanilla_klipper\]' $NS/printer_data/config/moonraker.conf | grep -qx 1 && grep -q 'origin: https://github.com/ducati1198/wm-ultra-fluidd-acepro-panel.git' $NS/printer_data/config/moonraker.conf && grep -q 'path: $NS/wm-ultra-fluidd-acepro-panel' $NS/printer_data/config/moonraker.conf && grep -q '^\[update_manager\]' $NS/printer_data/config/moonraker.conf && ls $NS/printer_data/config/moonraker.conf.wm-before-updatemgr-*"
check "ACE Pro: doctor is happy" "yes n | WM_HOME=$NS WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'ACE Pro driver and config are in place'"
rm -f "$NS/klipper/klippy/extras/ace"
check "ACE Pro: doctor notices the missing link and offers the fix" "yes n | WM_HOME=$NS WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'ACE Pro driver or its config is not set up'"
WM_HOME="$NS" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --doctor --fix-all >/dev/null 2>&1 </dev/null
check "ACE Pro: Fix everything puts the link back" "[ -L $NS/klipper/klippy/extras/ace ]"
check "--remove acepro asks first and keeps everything on no" "M 'n\n' $NS --remove acepro | grep -q 'Nothing changed' && [ -f $NS/printer_data/config/rpi_ace.cfg ] && [ -d $NS/wm-ultra-fluidd-acepro-panel ]"
check "--remove acepro removes configs, include lines, link and the project, keeps a copy of printer.cfg and the saved copies on no" "M 'y\nn\n' $NS --remove acepro | grep -q 'ACE Pro removed' && ! ls $NS/printer_data/config/rpi_ace*.cfg $NS/printer_data/config/rpi_endless.cfg $NS/printer_data/config/rpi_stats.cfg $NS/printer_data/config/rpi-ultra-install.conf 2>/dev/null && ! grep -q 'wm_ace\\|wm_endless\\|wm_stats' $NS/printer_data/config/printer.cfg && [ ! -e $NS/klipper/klippy/extras/ace ] && [ ! -e $NS/wm-ultra-fluidd-acepro-panel ] && [ -d $NS/acepro-backup ] && grep -q 'WANT_ACEPRO=0' $NS/wm-rpi-backup/install.conf"
check "--remove acepro also takes its Fluidd update entry out (the installer's own entry stays)" "! grep -q 'update_manager wm-ultra-fluidd-acepro-panel' $NS/printer_data/config/moonraker.conf && grep -q '^\[update_manager wm_ultra_vanilla_klipper\]' $NS/printer_data/config/moonraker.conf"
check "--remove acepro again says it is not installed" "M 'y\n' $NS --remove acepro | grep -q 'not installed'"
inst "$NS" --update --only-addon acepro --acepro on >/dev/null
rm -f "$NS/wm-ultra-fluidd-acepro-panel/installer.sh"
check "--remove acepro still works when the project's installer is gone, and can delete the saved copies" "M 'y\ny\n' $NS --remove acepro | grep -q 'ACE Pro removed' && ! ls $NS/printer_data/config/rpi_ace*.cfg 2>/dev/null && ! grep -q 'wm_ace' $NS/printer_data/config/printer.cfg && [ ! -L $NS/klipper/klippy/extras/ace ] && [ ! -e $NS/acepro-backup ] && [ ! -e $NS/wm-ultra-fluidd-acepro-panel ]"
unset WM_TEST_ACEPRO_SRC

sec "== screen board menu"
MB="$T/mb"; mkdir -p "$MB"
mb() { local in="$1"; shift; printf "$in" | WM_TEST_SERVICES="makerbase-client klipper moonraker nginx" WM_HOME="$MB" WM_INSTALLER_TEST=1 bash "$SB" "$@" 2>&1; }
check "board menu: lists every entry and exits with 0" "mb '0\n' --menu | grep -q 'Install KlipperScreen' && mb '0\n' --menu | grep -q 'Backup and restore' && mb '0\n' --menu | grep -q 'Dry run'"
check "board menu: settings page has the Pi address and network entries, and no screen driver entry" "mb '5\n0\n0\n' --menu | grep -q 'Change the Pi address' && mb '5\n0\n0\n' --menu | grep -q 'Network and system' && ! mb '5\n0\n0\n' --menu | grep -q 'Change the screen driver'"
check "board menu: check and fix page" "mb '3\n0\n0\n' --menu | grep -q 'Fix everything' && mb '3\n0\n0\n' --menu | grep -q 'Restart the screen'"
check "board menu: the header shows the installer version" "mb '0\n' --menu | grep -q \"installer $(tr -d '[:space:]' < $ROOT/VERSION)\""
check "board menu: a wrong choice is explained" "mb 'x\n0\n' --menu | grep -q 'Choose a number'"
check "board menu: status is read-only" "mb '3\n3\n0\n0\n' --menu | grep -q 'Screen board status' && [ ! -e $MB/.sudo.log ]"
check "board menu: dry run changes nothing" "mb '7\n192.0.2.10\n\n0\n' --menu | grep -q 'DRY RUN' && [ ! -e $MB/wm-screen-backup/disabled.list ]"
check "board menu: install from the menu asks for the Pi address" "mb '1\n192.0.2.10\n\n0\n' --menu | grep -q 'Connects to: http://192.0.2.10:7125'"
check "board --set-driver fbdev and back" "mb '' --set-driver fbdev | grep -q 'driver is now fbdev' && [ -e $MB/.fbdev ] && mb '' --set-driver modesetting | grep -q 'driver is now modesetting' && [ ! -e $MB/.fbdev ]"
check "board --set-driver refuses a wrong name" "! mb '' --set-driver nope"

MY="$T/my"; mkdir -p "$MY/printer_data/config"
myb() { WM_ASSUME_YES=1 WM_TEST_SERVICES="makerbase-client klipper moonraker nginx" WM_HOME="$MY" WM_INSTALLER_TEST=1 bash "$SB" "$@" 2>&1 </dev/null; }
check "board: a copy of screen_board.sh WITHOUT the helper next to it (Factory mode button, rescue, USB flag) still restores and does not say lib_free_space.sh is missing" "A=\$(mktemp -d); cp $SB \$A/wm-factory-restore; mkdir -p \$A/h; o=\$(WM_ASSUME_YES=1 WM_HOME=\$A/h WM_INSTALLER_TEST=1 bash \$A/wm-factory-restore --status 2>&1 </dev/null); r=\$?; rm -rf \$A; ! echo \"\$o\" | grep -qi 'is missing\|could not be read' && echo \"\$o\" | grep -q 'Screen board status'"
check "board: the --free-space helper missing next to a copy gives a clear message, not a crash" "A=\$(mktemp -d); cp $SB \$A/x.sh; mkdir -p \$A/h; o=\$(WM_ASSUME_YES=1 WM_HOME=\$A/h WM_INSTALLER_TEST=1 bash \$A/x.sh --free-space 2>&1 </dev/null); rm -rf \$A; echo \"\$o\" | grep -q 'not next to this copy'"
myb --pi 192.0.2.10 --no-reboot >/dev/null
check "board --doctor passes on a fresh install" "myb --doctor | grep -q 'No problems found'"
check "board --doctor finds a missing ZR Tools file" "rm -f $MY/KlipperScreen/panels/zr_tools.py; myb --doctor | grep -q 'ZR Tools file missing'"
check "board --backup writes a tgz with the config and the service list" "myb --backup | grep -q Saved && tar tzf \$(ls $MY/wm-screen-backups/*.tgz | head -1) | grep -q KlipperScreen.conf && tar tzf \$(ls $MY/wm-screen-backups/*.tgz | head -1) | grep -q disabled.list"
check "board --restore-backup restores and makes a safety copy" "echo changed > $MY/printer_data/config/zr_screen.conf; myb --restore-backup 1 | grep -q 'Settings restored' && ! grep -q changed $MY/printer_data/config/zr_screen.conf && [ \$(ls $MY/wm-screen-backups/*.tgz | wc -l) -ge 2 ]"
check "board --support-bundle has the config and a system page" "myb --support-bundle | grep -q Saved && tar tzf \$(ls $MY/wm-screen-support-*.tgz | head -1) | grep -q KlipperScreen.conf && tar tzf \$(ls $MY/wm-screen-support-*.tgz | head -1) | grep -q system.txt"
UPD="$T/upd"; mkdir -p "$UPD/zr_tools" "$UPD/scripts"; echo 99.0.0 > "$UPD/VERSION"; for f in zr_tools zr_views zr_logic pi_address_panel; do echo new > "$UPD/zr_tools/$f.py"; done; cp "$SB" "$ROOT/scripts/lib_free_space.sh" "$UPD/scripts/"
check "board --update copies the new panels after a backup" "WM_TEST_UPDATE_DIR=$UPD myb --update | grep -q 'Updated to 99.0.0' && grep -q new $MY/KlipperScreen/panels/zr_views.py"
check "board --update remembers the installed version (the Update button compares with it) and takes the installer folder from the saved path when run as a lone copy" "[ \"\$(cat $MY/wm-screen-backup/version)\" = 99.0.0 ] && A=\$(mktemp -d) && cp $SB \$A/wm-factory-restore && mkdir -p \$A/inst/zr_tools && echo 5.5.5 > \$A/inst/VERSION && touch \$A/inst/zr_tools/zr_tools.py && mkdir -p \$A/h/wm-screen-backup && echo \$A/inst > \$A/h/wm-screen-backup/installer_dir && WM_TEST_UPDATE_DIR=$UPD WM_HOME=\$A/h WM_INSTALLER_TEST=1 bash \$A/wm-factory-restore --whats-new 2>&1 </dev/null | grep -q 'Installed: 5.5.5'; r=\$?; rm -rf \$A; [ \$r = 0 ]"
check "board --update --yes --detach runs in test mode without systemd-run (the Update button command)" "U2=\$(mktemp -d); cp -a $UPD/. \$U2/; echo 99.0.1 > \$U2/VERSION; WM_TEST_UPDATE_DIR=\$U2 myb --update --yes --detach | grep -q 'Updated to 99.0.1'; r=\$?; rm -rf \$U2; [ \$r = 0 ]"
check "board: the sudoers line allows exactly the Factory mode and the Update commands" "grep -q '^write_restore_sudoers() {' $SB && grep -q -- '--factory-restore --yes --detach, %s --update --yes --detach' $SB"
check "board --post-update (re)applies the button permissions and writes the version marks (also from an update run by an older script)" "PU=\$(mktemp -d); mkdir -p \$PU/KlipperScreen/panels; cp -a $UPD/. \$PU/new/ 2>/dev/null; for f in zr_tools zr_views zr_logic; do cp $UPD/zr_tools/\$f.py \$PU/KlipperScreen/panels/; done; mkdir -p \$PU/new/scripts; cp $SB $ROOT/scripts/lib_free_space.sh \$PU/new/scripts/; WM_INSTALLER_DIR=\$PU/wm_ultra_vanilla_klipper WM_HOME=\$PU WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash \$PU/new/scripts/screen_board.sh --post-update --yes 2>&1 </dev/null | grep -q 'Done'; r=\$?; v=\$(cat \$PU/wm-screen-backup/version 2>/dev/null); p=\$(cat \$PU/KlipperScreen/panels/zr_version.txt 2>/dev/null); rm -rf \$PU; [ \$r = 0 ] && [ \"\$v\" = 99.0.0 ] && [ \"\$p\" = 99.0.0 ]"
check "board --update writes zr_version.txt next to the panels (the screen reads its own version there)" "grep -q '^99\\.0\\.' $MY/KlipperScreen/panels/zr_version.txt"
check "board --update with a SCREEN_VERSION writes the screen marks (zr_screen_version.txt and wm-screen-backup/screen_version)" "US=\$(mktemp -d); cp -a $UPD/. \$US/; echo 99.1.0 > \$US/VERSION; echo S9.0.0 > \$US/SCREEN_VERSION; echo 99.1.0 > \$US/SCREEN_NEEDS_PI; WM_TEST_UPDATE_DIR=\$US myb --update | grep -q 'Updated to S9.0.0'; r=\$?; rm -rf \$US; [ \$r = 0 ] && [ \"\$(cat $MY/KlipperScreen/panels/zr_screen_version.txt)\" = S9.0.0 ] && [ \"\$(cat $MY/wm-screen-backup/screen_version)\" = S9.0.0 ] && [ \"\$(cat $MY/wm-screen-backup/screen_needs_pi)\" = 99.1.0 ]"
check "board --update: a Pi-only release (new VERSION, same SCREEN_VERSION) is Already up to date and changes nothing" "US=\$(mktemp -d); cp -a $UPD/. \$US/; echo 99.2.0 > \$US/VERSION; echo S9.0.0 > \$US/SCREEN_VERSION; echo keep2 > $MY/KlipperScreen/panels/zr_views.py; for f in zr_tools zr_logic; do cp $MY/KlipperScreen/panels/\$f.py \$US/zr_tools/\$f.py; done; cp $MY/KlipperScreen/panels/zr_views.py \$US/zr_tools/zr_views.py; WM_TEST_UPDATE_DIR=\$US myb --update | grep -q 'Already up to date'; r=\$?; rm -rf \$US; [ \$r = 0 ]"
check "board --update on an up-to-date board still repairs missing version marks and button permissions" "U3=\$(mktemp -d); cp -a $UPD/. \$U3/; cp $ROOT/VERSION \$U3/VERSION; for f in zr_tools zr_views zr_logic; do cp $MY/KlipperScreen/panels/\$f.py \$U3/zr_tools/\$f.py; done; cp $ROOT/VERSION $MY/wm-screen-backup/version; rm -f $MY/KlipperScreen/panels/zr_version.txt; WM_TEST_POST_UPDATE=1 WM_TEST_UPDATE_DIR=\$U3 myb --update > \$U3.out; grep -q 'fixing that now' \$U3.out; r=\$?; rm -f \$U3.out; rm -rf \$U3; [ \$r = 0 ] && [ -f $MY/KlipperScreen/panels/zr_version.txt ]"
check "board --update after a git pull (version marks say new, panel files are old) refreshes the files instead of saying up to date, and --post-update does not stamp a version the files are not" "U5=\$(mktemp -d); cp -a $UPD/. \$U5/; echo 98.0.0 > $MY/KlipperScreen/panels/zr_version.txt; echo 98.0.0 > \$U5/VERSION; echo changed > \$U5/zr_tools/zr_logic.py; echo old > $MY/KlipperScreen/panels/zr_logic.py; WM_TEST_UPDATE_DIR=\$U5 myb --update > \$U5.out; grep -q 'Refreshing them' \$U5.out; r=\$?; rm -f \$U5.out; rm -rf \$U5; [ \$r = 0 ] && grep -q changed $MY/KlipperScreen/panels/zr_logic.py"
check "board --update never goes back to an older version (a stale GitHub copy): says so and changes nothing" "U4=\$(mktemp -d); cp -a $UPD/. \$U4/; echo 0.0.1 > \$U4/VERSION; echo keep > $MY/KlipperScreen/panels/zr_views.py; WM_TEST_UPDATE_DIR=\$U4 myb --update | grep -q 'OLDER than the one installed'; r=\$?; rm -rf \$U4; [ \$r = 0 ] && grep -q keep $MY/KlipperScreen/panels/zr_views.py"
check "board: every GitHub read of the updater and the screen button has a cache buster" "grep -c 'nocache=' $SB | grep -qv '^[01]\$' && grep -q 'nocache=' $ROOT/zr_tools/zr_logic.py"
check "board --update backup is named before-update and only the newest 5 stay (own backups kept)" "for i in 1 2 3 4 5 6 7; do touch -d 2020-01-0\$i $MY/wm-screen-backups/screen-backup-old\$i-before-update.tgz; done; touch $MY/wm-screen-backups/screen-backup-mine.tgz; sed -i 's/^99.0.0$/99.0.1/' $UPD/VERSION; WM_TEST_UPDATE_DIR=$UPD myb --update >/dev/null 2>&1; [ \$(ls $MY/wm-screen-backups/*before-update.tgz | wc -l) -le 5 ] && [ -f $MY/wm-screen-backups/screen-backup-mine.tgz ]"
check "board --system shows host name and sets a time zone" "myb --system | grep -q 'Host name' && myb --system tz:America/Toronto | grep -q 'Time zone is America/Toronto' && ! myb --system tz:'bad zone!'"
check "board --log and --restart-screen run" "myb --log | grep -q 'Last log' && myb --restart-screen | grep -q restarted"

MU="$T/mu"; mkdir -p "$MU/printer_data/config"; FK="$T/wm_ultra_vanilla_klipper-fake"; mkdir -p "$FK/scripts"; cp "$SB" "$ROOT/scripts/lib_free_space.sh" "$FK/scripts/"; echo 1.0.0 > "$FK/VERSION"
muf() { WM_ASSUME_YES=1 WM_TEST_SERVICES="makerbase-client klipper moonraker nginx" WM_HOME="$MU" WM_INSTALLER_TEST=1 bash "$FK/scripts/screen_board.sh" "$@" 2>&1 </dev/null; }
muf --pi 192.0.2.10 --no-reboot >/dev/null; muf --backup >/dev/null; muf --support-bundle >/dev/null
check "board --remove restoredata is refused while KlipperScreen is installed" "! muf --remove restoredata && [ -d $MU/wm-screen-backup ]"
check "board --remove rescue removes the rescue tool and the Factory mode button, KlipperScreen stays" "muf --remove rescue | grep -q 'Rescue tool and Factory mode button removed' && grep -q 'remove factory button' $MU/.sudo.log && [ -d $MU/KlipperScreen ]"
check "board --remove backups deletes backups and bundles" "muf --remove backups | grep -q 'deleted' && [ ! -d $MU/wm-screen-backups ] && ! ls $MU/wm-screen-support-*.tgz"
check "board --remove with a wrong name is refused" "! muf --remove nope"
check "board --remove installer refuses a folder that is not a wm_ultra_vanilla_klipper copy" "mkdir -p $T/other/scripts && cp $SB $ROOT/scripts/lib_free_space.sh $T/other/scripts/ && echo 1 > $T/other/VERSION && WM_ASSUME_YES=1 WM_HOME=$MU WM_INSTALLER_TEST=1 bash $T/other/scripts/screen_board.sh --remove installer </dev/null | grep -q 'not removing' && [ -d $T/other ]"
check "board menu: uninstall page lists the four entries" "mb '9\n0\n0\n' --menu | grep -q 'Rescue tool + Factory mode button' && mb '9\n0\n0\n' --menu | grep -q 'Downloaded installer folder'"
muf --factory-restore --no-reboot >/dev/null
check "board --remove restoredata works once KlipperScreen is gone" "muf --remove restoredata | grep -q 'deleted' && [ ! -d $MU/wm-screen-backup ]"
check "board --remove installer deletes the downloaded folder" "muf --remove installer | grep -q 'Installer folder deleted' && [ ! -d $FK ]"

check "board: no options at a terminal opens the menu" "printf '0\n' | WM_TEST_MENU_DEFAULT=1 WM_HOME=$MB WM_INSTALLER_TEST=1 bash $SB 2>&1 | grep -q 'Install KlipperScreen + ZR Tools'"
check "board: --install skips the menu" "! printf '0\n' | WM_TEST_MENU_DEFAULT=1 WM_HOME=$MB WM_INSTALLER_TEST=1 bash $SB --install --yes 2>&1 | grep -q 'Choose:'"

sec "== update without git / dry run in the menu"
GL="$T/gl"; mkdir -p "$GL"; cp -a "$ROOT"/. "$GL"/ 2>/dev/null; rm -rf "$GL/.git"; echo 99.0.0 > "$T/gl_new_version"
GN="$T/gl_new"; rm -rf "$GN"; mkdir -p "$GN"; cp -a "$ROOT"/. "$GN"/ 2>/dev/null; rm -rf "$GN/.git"; echo 99.0.0 > "$GN/VERSION"; echo marker > "$GN/NEWFILE"
GH="$T/glh"; mkdir -p "$GH"
glx() { WM_ASSUME_YES=1 WM_TEST_UPDATE_DIR="$GN" WM_TEST_NO_FETCH=1 WM_HOME="$GH" WM_INSTALLER_TEST=1 bash "$GL/installer.sh" "$@" 2>&1 </dev/null; }
check "--get-latest in a folder without git replaces the files" "glx --get-latest | grep -q 'updated to 99.0.0' && [ -f $GL/NEWFILE ] && grep -q 99.0.0 $GL/VERSION"
check "--get-latest says up to date when the version is the same" "glx --get-latest | grep -q 'Already up to date'"
GL2="$T/gl2"; mkdir -p "$GL2"; cp -a "$ROOT"/. "$GL2"/; rm -rf "$GL2/.git"
check "--get-latest --dry-run changes nothing" "WM_ASSUME_YES=1 WM_TEST_UPDATE_DIR=$GN WM_HOME=$GH WM_INSTALLER_TEST=1 bash $GL2/installer.sh --get-latest --dry-run </dev/null 2>&1 | grep -q 'would copy' && [ ! -f $GL2/NEWFILE ]"
check "--check-updates works without git (version compare)" "WM_TEST_NEW_VERSION=99.0.0 WM_HOME=$GH WM_INSTALLER_TEST=1 bash $GL2/installer.sh --check-updates </dev/null 2>&1 | grep -q 'On GitHub:   installer 99.0.0'"
check "menu: main page has Dry run of the install" "M '0\n' $HR --menu | grep -q 'Dry run of the install'"
check "menu: dry run entry shows the plan and changes nothing" "rm -rf $T/dr; mkdir -p $T/dr; M '8\n\n0\n' $T/dr --menu | grep -q 'DRY RUN' && [ ! -d $T/dr/klipper ]"

sec "== damaged factory files"
RF="$T/rf"; rm -rf "$RF"; mkdir -p "$RF"; git clone -q "$ROOT" "$RF" 2>/dev/null && cp "$ROOT/installer.sh" "$RF/installer.sh" 2>/dev/null && mkdir -p "$RF/scripts" && cp "$ROOT/scripts/lib_free_space.sh" "$RF/scripts/"
rm -f "$RF"/factory/ultra-s/klipper/klippy/extras/air.py
RFH="$T/rfh"; mkdir -p "$RFH"
check "install notices missing factory files, restores them and goes on" "WM_ASSUME_YES=1 WM_HOME=$RFH WM_INSTALLER_TEST=1 bash $RF/installer.sh --from-github --model ultra-s </dev/null 2>&1 | grep -q 'Factory files restored' && [ -f $RF/factory/ultra-s/klipper/klippy/extras/air.py ]"

check "menu: Update now on an empty Pi explains instead of failing" "rm -rf $T/ue; mkdir -p $T/ue; M '2\n2\n\n0\n0\n' $T/ue --menu | grep -q 'Nothing is installed on this Pi yet' "
check "--update on an empty Pi says what to do" "WM_HOME=$T/ue WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --update </dev/null 2>&1 | grep -q 'nothing is installed by this installer yet'"

sec "== Wi-Fi power saving off and the Wi-Fi watchdog (B-041)"
WF="$T/wifi"; mkdir -p "$WF/printer_data/config"
wifi() { WM_TEST_WIFI_DEV="$1" WM_TEST_NM="$2" WM_HOME="$WF" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --wifi 2>&1 </dev/null; }
rm -f "$WF/.sudo.log"; OUTW="$(wifi wlan0 1)"
check "Wi-Fi with NetworkManager: power saving off on the active connection, a copy of the connection kept, no watchdog installed (2.19.1)" "grep -q 'wifi powersave off (testwifi, was default)' $WF/.sudo.log && ! grep -q 'wifi watchdog installed' $WF/.sudo.log && echo \"\$OUTW\" | grep -q 'Wi-Fi power saving off' && ls -d $WF/wm-rpi-backup/wifi-*"
rm -f "$WF/.sudo.log"
WB="$T/wifibus"; rm -rf "$WB"; mkdir -p "$WB/printer_data/config"; printf '[all]\narm_64bit=1\n' > "$WB/boot-config.txt"
wifib() { WM_TEST_WIFI_DEV=wlan0 WM_TEST_NM=1 WM_TEST_PI_MODEL="$1" WM_HOME="$WB" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --wifi 2>&1 </dev/null; }
OUTB="$(wifib 'Raspberry Pi 400 Rev 1.0')"
check "Wi-Fi bus (F-196): a Pi 400 is left alone" "! grep -q sdio_overclock $WB/boot-config.txt"
OUTB="$(wifib 'Raspberry Pi 4 Model B Rev 1.5')"
check "Wi-Fi bus (F-196): a Raspberry Pi 4 Model B on Wi-Fi gets dtparam=sdio_overclock=25 once, with a copy of the old file" "[ \$(grep -c '^dtparam=sdio_overclock=25' $WB/boot-config.txt) = 1 ] && grep -q 'arm_64bit=1' $WB/boot-config.txt && ls $WB/wm-rpi-backup/wifi-bus-*/config.txt"
OUTB="$(wifib 'Raspberry Pi 4 Model B Rev 1.5')"
check "Wi-Fi bus (F-196): a second run adds nothing" "[ \$(grep -c 'sdio_overclock' $WB/boot-config.txt) = 1 ] && echo \"$OUTB\" | grep -q 'already set'"
check "Wi-Fi: a second run changes nothing" "wifi wlan0 1 | grep -q 'power saving is off' && [ ! -f $WF/.sudo.log ]"
check "Wi-Fi: a Pi on a cable is left alone" "rm -f $WF/.wifi_powersave; wifi eth0 1 | grep -q 'not Wi-Fi: nothing to do' && [ ! -f $WF/.sudo.log ]"
check "Wi-Fi without NetworkManager: power saving left as it is, it says why" "wifi wlan0 0 | grep -q 'without NetworkManager' && [ ! -f $WF/.sudo.log ]"
check "Wi-Fi: install and update run the step, uninstall stops an old watchdog, the doctor checks it" "grep -q 'step_screen; step_wifi;' $ROOT/installer.sh && grep -q 'step_wm_modules; step_wifi; step_logs' $ROOT/installer.sh && grep -q 'SUDO systemctl stop wm-wifi-watchdog' $ROOT/installer.sh && grep -q 'offer_fix \"turn Wi-Fi power saving off' $ROOT/installer.sh"
check "Wi-Fi watchdog removed (2.19.1): no script, no service file in the repo, the installer installs none" "[ ! -e $ROOT/scripts/wm-wifi-watchdog ] && [ ! -e $ROOT/config/wm-wifi-watchdog.service ] && ! grep -q 'SUDO install .*wm-wifi-watchdog' $ROOT/installer.sh"
mkdir -p "$WF/.wifiwd"; echo old > "$WF/.wifiwd/wm-wifi-watchdog"; rm -f "$WF/.sudo.log"; rm -f "$WF/.wifi_powersave"
check "Wi-Fi: an old watchdog is stopped and deleted at the next run" "wifi wlan0 1 >/dev/null; grep -q 'wifi watchdog removed' $WF/.sudo.log && [ ! -e $WF/.wifiwd/wm-wifi-watchdog ]"
mkdir -p "$WF/.wifiwd"; echo old > "$WF/.wifiwd/wm-wifi-watchdog"; rm -f "$WF/.sudo.log"
check "Wi-Fi: an old watchdog is deleted on a Pi on a cable too" "wifi eth0 1 >/dev/null; grep -q 'wifi watchdog removed' $WF/.sudo.log && [ ! -e $WF/.wifiwd/wm-wifi-watchdog ]"
mkdir -p "$WF/.wifiwd"; echo old > "$WF/.wifiwd/wm-wifi-watchdog"; rm -f "$WF/.sudo.log"
check "Wi-Fi: a dry run only says it would delete the old watchdog" "WM_TEST_WIFI_DEV=wlan0 WM_TEST_NM=1 WM_HOME=$WF WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --wifi --dry-run </dev/null 2>&1 | grep -q 'would stop and delete the old wm-wifi-watchdog' && [ -e $WF/.wifiwd/wm-wifi-watchdog ] && [ ! -f $WF/.sudo.log ]"
rm -rf "$WF/.wifiwd"; rm -f "$WF/.sudo.log"

sec "== troubleshooting logs, black box and the support bundle (item 30, F-107, F-022)"
LGX="$T/logsx"; mkdir -p "$LGX/printer_data/config" "$LGX/printer_data/logs"
logsrun() { WM_HOME="$LGX" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" "$@" 2>&1 </dev/null; }
rm -f "$LGX/.sudo.log"; OUTL="$(logsrun --logs)"
check "logs: --logs installs the digest script and its service, the black box and the on-disk system log" "cmp -s $ROOT/scripts/wm_log_digest.py $LGX/printer_data/scripts/wm_log_digest.py && grep -q 'wm-log-digest.service' $LGX/.sudo.log && grep -q 'blackbox installed' $LGX/.sudo.log && grep -q 'systemctl restart systemd-journald' $LGX/.sudo.log && grep -q 'systemctl enable wm-log-digest' $LGX/.sudo.log && grep -q 'systemctl enable wm-blackbox' $LGX/.sudo.log && echo \"\$OUTL\" | grep -q 'Troubleshooting logs installed' && echo \"\$OUTL\" | grep -q 'Black box installed'"
rm -f "$LGX/.sudo.log"
check "logs: a second run changes nothing" "logsrun --logs | grep -q 'are written' && logsrun --logs | grep -q 'Pi is recorded every 10 s' && [ ! -f $LGX/.sudo.log ]"
check "logs: --dry-run shows the steps and changes nothing" "LGD=$T/logsd; mkdir -p \$LGD/printer_data/config; WM_HOME=\$LGD WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --logs --dry-run </dev/null 2>&1 | grep -q 'would install wm_log_digest.py' && [ ! -e \$LGD/printer_data/scripts/wm_log_digest.py ]"
check "logs: an old script on the Pi is replaced at the next run" "echo '# old' > $LGX/printer_data/scripts/wm_log_digest.py; logsrun --logs | grep -q 'Troubleshooting logs installed' && cmp -s $ROOT/scripts/wm_log_digest.py $LGX/printer_data/scripts/wm_log_digest.py"
check "logs: install and update run both steps, uninstall stops both services, the doctor checks both" "grep -q 'step_screen; step_wifi; step_logs; step_blackbox;' $ROOT/installer.sh && grep -q 'step_wm_modules; step_wifi; step_logs; step_blackbox; fi' $ROOT/installer.sh && grep -q 'SUDO systemctl stop wm-log-digest' $ROOT/installer.sh && grep -q 'SUDO systemctl stop wm-blackbox' $ROOT/installer.sh && grep -q 'offer_fix \"install the troubleshooting logs\" step_logs' $ROOT/installer.sh && grep -q 'offer_fix \"install the black box\" step_blackbox' $ROOT/installer.sh"
check "logs: the doctor says when they are missing" "LGM=$T/logsdoc; mkdir -p \$LGM/printer_data/config; WM_HOME=\$LGM WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --doctor </dev/null 2>&1 | grep -q 'the troubleshooting log service is not installed'"
check "logs: the service runs as t13dp and starts the script from printer_data/scripts" "grep -q '^User=t13dp' $ROOT/config/wm-log-digest.service && grep -q 'ExecStart=/usr/bin/python3 /home/t13dp/printer_data/scripts/wm_log_digest.py' $ROOT/config/wm-log-digest.service && grep -q 'Restart=on-failure' $ROOT/config/wm-log-digest.service"
check "logs: the digest only reads (no write to Klipper files, no restart, no gcode sent)" "python3 -I -m py_compile $ROOT/scripts/wm_log_digest.py && ! grep -vE '^\s*#' $ROOT/scripts/wm_log_digest.py | grep -qE 'gcode/script|server/restart|printer/restart|firmware_restart|systemctl|os\.system|shell=True' && [ "$(grep -vE '^\s*#' $ROOT/scripts/wm_log_digest.py | grep -c 'subprocess.run')" = 2 ] && grep -q 'cmd = \[.journalctl., .--no-pager.' $ROOT/scripts/wm_log_digest.py"
check "logs: the size limits are in the script (1 MB events, 1 MB ace, 120 and 200 lines a minute)" "grep -q '^MAX_BYTES = 1000000' $ROOT/scripts/wm_log_digest.py && grep -q '^ACE_MAX = 1000000' $ROOT/scripts/wm_log_digest.py && grep -q '> 120' $ROOT/scripts/wm_log_digest.py && grep -q '> 200' $ROOT/scripts/wm_log_digest.py"
check "black box: the script is valid, never reboots and never restarts Klipper, the unit restarts it" "bash -n $ROOT/scripts/wm-blackbox && ! grep -vE '^\s*#' $ROOT/scripts/wm-blackbox | grep -qE '(^[[:space:]]*|;[[:space:]]*|&&[[:space:]]*)(reboot|shutdown|systemctl (reboot|restart|stop)) ' && grep -q 'Restart=always' $ROOT/config/wm-blackbox.service && grep -q 'Storage=persistent' $ROOT/config/50-wm-persistent.conf"
check "digest: python tests (rules, limits, rotation, config check)" "python3 -I -W ignore $ROOT/tests/test_log_digest.py"
LGL="$LGX/printer_data/logs"
printf '2026-11-17 09:00:00  START     Klipper started\n2026-11-17 09:00:05  CONFIG    token: abc123secret\n' > "$LGL/wm-events.log"
printf 'WonderMaker config check\nResult: 0 problems\n' > "$LGL/wm-config-check.log"
printf '2026-11-17 09:00:01  ACE[0] Disconnected\n' > "$LGL/wm-ace.log"
printf '2026-11-17 09:00:00 up=10s power=0x0 ok temp=40.0 host=10.1.2.3\n' > "$LGL/wm-blackbox.log"
printf 'Nov 17 09:00:00 klipper started\n' > "$LGL/wm-system.log"; printf 'old ace\n' > "$LGL/wm-ace.log.2"
printf 'mr\n' > "$LGL/moonraker.log"; printf 'ks\n' > "$LGL/KlipperScreen.log"; printf 'cn\n' > "$LGL/crowsnest.log"
printf 'Stats 1.0: gcodein=0\nStart printer at Tue (1.0 2.0)\n===== Config file =====\n[gcode_macro SECRETMACRO]\ngcode:\n\tM117 x\n=======================\nLoaded MCU mcu\nTransition to shutdown state: test\nStats 2.0: gcodein=0\n' > "$LGL/klippy.log"
WM_HOME="$LGX" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --support-bundle >/dev/null 2>&1 </dev/null
SBL="$(ls $LGX/wm-support-*.tgz | head -1)"
check "support bundle: holds the new logs, the real klippy lines, the file list and says where to look" "tar tzf $SBL | grep -q 'logs/wm-events.log' && tar tzf $SBL | grep -q 'logs/wm-config-check.log' && tar tzf $SBL | grep -q 'logs/wm-ace.log' && tar tzf $SBL | grep -q 'logs/wm-blackbox.log' && tar tzf $SBL | grep -q 'logs/klippy-real.log' && tar tzf $SBL | grep -q 'files-and-versions.txt' && tar xzOf $SBL | grep -q 'Where to look first'"
check "support bundle: klippy-real.log has the real lines but not the config copy or the Stats lines" "tar xzOf $SBL wm-support/logs/klippy-real.log | grep -q 'Transition to shutdown state: test' && ! tar xzOf $SBL wm-support/logs/klippy-real.log | grep -qE 'SECRETMACRO|^Stats'"
check "support bundle: the new logs are scrubbed too" "! tar xzOf $SBL wm-support/logs/wm-events.log | grep -q abc123secret && ! tar xzOf $SBL wm-support/logs/wm-blackbox.log | grep -q '10.1.2.3'"
check "support bundle: the service list in the report has the new services" "tar xzOf $SBL wm-support/system.txt | grep -q 'wm-log-digest' && tar xzOf $SBL wm-support/system.txt | grep -q 'wm-blackbox'"

check "support bundle: holds wm-system.log, the ACE log's second old file and the Moonraker, KlipperScreen and crowsnest logs" "tar tzf $SBL | grep -q 'logs/wm-system.log' && tar tzf $SBL | grep -q 'logs/moonraker.log' && tar tzf $SBL | grep -q 'logs/KlipperScreen.log' && tar tzf $SBL | grep -q 'logs/crowsnest.log' && tar tzf $SBL | grep -q 'logs/wm-ace.log.2'"
check "support bundle: the where-to-look text names wm-system.log" "tar xzOf $SBL wm-support/README.txt | grep -q 'wm-system.log'"
check "log digest: a WMLOG line from the console (echo: or //) becomes a STATE line, the other console lines do not" "[ \$(python3 $ROOT/scripts/wm_log_digest.py --selftest | grep -c '  STATE     PAUSE start T0 gcode') = 1 ]"
check "log digest: wm-system.log and the 1 MB ACE log with two old files are in the script" "grep -q 'wm-system.log' $ROOT/scripts/wm_log_digest.py && grep -q 'ACE_MAX = 1000000' $ROOT/scripts/wm_log_digest.py && grep -q 'ACELOG + \".2\"' $ROOT/scripts/wm_log_digest.py"
for MD in ultra ultra-s; do
check "macros $MD: _WM_LOG_STATE exists and PAUSE, RESUME and CANCEL_PRINT each call it twice" "F=$ROOT/factory/$MD/config/macros.cfg; grep -q '^\[gcode_macro _WM_LOG_STATE\]' \$F && for w in PAUSE_START PAUSE_PARKED RESUME_START RESUME_DONE CANCEL_START CANCEL_DONE; do grep -q \"_WM_LOG_STATE WHAT=\$w\\\$\" \$F || exit 1; done"
done

sec "== one folder for every backup (item 36)"
UBX="$T/ubx"; mkdir -p "$UBX/printer_data/config" "$UBX/wm-backups" "$UBX/acepro-backup" "$UBX/fluidd_backup_a" "$UBX/fluidd_backup_b" "$UBX/wm-rpi-backup" "$UBX/repo/.git"
for n in a b c; do echo $n > "$UBX/printer_data/config/rpi_base.cfg.wm-before-$n-2026111${#n}-100000"; sleep 0.01; done
touch -d "2026-11-10" "$UBX/printer_data/config/rpi_base.cfg.wm-before-a-20261111-100000"; touch -d "2026-11-11" "$UBX/printer_data/config/rpi_base.cfg.wm-before-b-20261111-100000"
echo g > "$UBX/printer_data/config/saved_variables.cfg.wm-good"; echo t > "$UBX/wm-backups/wm-backup-x.tgz"; echo j > "$UBX/acepro-backup/m.json"; echo c > "$UBX/fluidd_backup_a/config.json"; echo c > "$UBX/fluidd_backup_b/config.json"; touch -d "2026-11-10" "$UBX/fluidd_backup_a"; touch -d "2026-11-14" "$UBX/fluidd_backup_b"; echo r > "$UBX/wm-rpi-backup/install.conf"
ubrun() { WM_HOME="$UBX" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" "$@" 2>&1 </dev/null; }
check "ultra backup: --ultra-backup --dry-run shows what would move and changes nothing" "ubrun --ultra-backup --dry-run | grep -q 'would move' && [ -f $UBX/wm-backups/wm-backup-x.tgz ] && [ ! -d $UBX/ultra-backup ]"
OUTU="$(ubrun --ultra-backup)"
check "ultra backup: old backups move into ~/ultra-backup, sorted by type" "[ -f $UBX/ultra-backup/settings/wm-backup-x.tgz ] && ls $UBX/ultra-backup/fluidd-macros/*/m.json >/dev/null && ls $UBX/ultra-backup/fluidd-page/*/fluidd_backup_a/config.json >/dev/null && [ ! -e $UBX/wm-backups ] && [ ! -e $UBX/acepro-backup ] && [ ! -e $UBX/fluidd_backup_a ] && [ -f $UBX/fluidd_backup_b/config.json ]"
check "ultra backup: every config copy moves to printer_data/config/backup (F-157), the safeguard copy never moves" "! ls $UBX/printer_data/config/rpi_base.cfg.wm-before-* 2>/dev/null && ls $UBX/printer_data/config/backup/rpi_base.cfg.wm-before-* | wc -l | grep -q '^3\$' && [ -f $UBX/printer_data/config/saved_variables.cfg.wm-good ]"
check "ultra backup: the installer records and git folders stay where they are" "[ -f $UBX/wm-rpi-backup/install.conf ] && [ -d $UBX/repo/.git ]"
check "ultra backup: INDEX.txt says where each backup came from" "grep -q 'moved ~/wm-backups/wm-backup-x.tgz -> ~/ultra-backup/settings/wm-backup-x.tgz' $UBX/ultra-backup/INDEX.txt"
check "ultra backup: a second run changes nothing" "ubrun --ultra-backup | grep -q 'Backups: all in ~/ultra-backup'"
check "ultra backup: the helper is copied next to the other helpers and recorded" "cmp -s $ROOT/scripts/wm_ultra_backup.py $UBX/printer_data/wm-tools/wm_ultra_backup.py"
check "ultra backup: the doctor says when backups are lying around, and fixes it" "UBD=$T/ubd; mkdir -p \$UBD/printer_data/config \$UBD/wm-backups; echo t > \$UBD/wm-backups/wm-backup-y.tgz; UBO=\$(WM_HOME=\$UBD WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --doctor </dev/null 2>&1); echo \"\$UBO\" | grep -q 'Backups: some are outside ~/ultra-backup' && [ -f \$UBD/ultra-backup/settings/wm-backup-y.tgz ]"
check "ultra backup: install, update and the --ultra-backup option run the step, the size limit is 400 MB" "grep -q '^step_ultrabackup   # after the panel and the add-ons, which write' $ROOT/installer.sh && grep -q '\[ -n \"\$ONLY_ADDON\" \] || step_ultrabackup   # last, after the panel and the add-ons' $ROOT/installer.sh && grep -q 'ultrabackup) step_ultrabackup' $ROOT/installer.sh && grep -q '^TOTAL_LIMIT = 400 \* MB' $ROOT/scripts/wm_ultra_backup.py"
check "ultra backup: python tests (moves, limits, records, disk guard)" "python3 -I -W ignore $ROOT/tests/test_ultra_backup.py"
check "macro index: python tests (index, no doubling, backup, rpi_pi.cfg rewrite keeps it)" "python3 -I -W ignore $ROOT/tests/test_cfg_index.py"
check "macro index: the repo copies of the config files carry an up-to-date index" "python3 -I $ROOT/scripts/wm_cfg_index.py file $ROOT/rpi-cfg/rpi_base.cfg $ROOT/rpi-cfg/rpi_calibration.cfg $ROOT/rpi-cfg/rpi_nozzle.cfg $ROOT/zr_tools/zr_tools.cfg; [ \$? = 0 ]"

sec "== touchscreen board status for the Fluidd Toolheads card"
check "screen board service: GET /status with version, latest, CPU, memory; uploaded every 60 s as wm_screen_status.json" "python3 -I - $ROOT/zr_tools/wm-chamber-light-http <<'PY'
import importlib.machinery, importlib.util, sys
l = importlib.machinery.SourceFileLoader('w', sys.argv[1]); sp = importlib.util.spec_from_loader('w', l); m = importlib.util.module_from_spec(sp); l.exec_module(m)
m.STATE['latest_at'] = 9e18; m.STATE['latest'] = '9.9.9'
st = m.status()
assert set(st) >= {'version', 'latest', 'cpu', 'screen_cpu', 'mem_free_mb', 'uptime_s', 'klipperscreen'}, st
assert st['latest'] == '9.9.9' and st['mem_free_mb'] > 0
src = open(sys.argv[1]).read()
assert 'wm_screen_status.json' in src and 'def status_loop' in src and 'self.path.rstrip(\"/\") == \"/status\"' in src
PY"

sec "== progress bars"
PB="$T/pb"; rm -rf "$PB"; mkdir -p "$PB"
OUT="$(inst "$PB" --from-github --model ultra-s)"
check "pi install: every step shows a bar with its number and percent" "echo \"$OUT\" | grep -q 'Step 1 of 14' && echo \"$OUT\" | grep -q 'Step 7 of 14' && echo \"$OUT\" | grep -q '  0%' && echo \"$OUT\" | grep -qE '█.*░.*[0-9]+%'"
check "pi install: ends with a full bar" "echo \"$OUT\" | grep -q '100%  All 14 steps finished'"
check "pi install: the host MCU step runs (Step 7b), builds from the pinned Klipper source and installs the service" "echo \"$OUT\" | grep -q 'Step 7b' && grep -q 'host mcu build + install klipper-mcu' $PB/.sudo.log && grep -q 'host mcu build + install klipper-mcu from' $PB/.sudo.log && grep -q '^klipper-upstream|https://github.com/Klipper3d/klipper|[0-9a-f]\{40\}$' $ROOT/config/pins/addons.txt"
check "host MCU: builds from the bundled Klipper (version file shipped, tracked and in SHA256SUMS), same version as the host" "(for m in ultra ultra-s; do [ -s $ROOT/factory/\$m/klipper/klippy/.version ] && grep -q 'klipper/klippy/.version' $ROOT/factory/\$m/SHA256SUMS && git -C $ROOT ls-files --error-unmatch factory/\$m/klipper/klippy/.version >/dev/null 2>&1 || exit 1; done); grep -q 'src/linux/main.c' $ROOT/installer.sh && grep -q 'KCONFIG_CONFIG=' $ROOT/installer.sh && grep -q '.built-from' $ROOT/installer.sh"
check "host MCU: printer.cfg is not changed by it and moonraker.asvc lists klipper_mcu" "! grep -q 'mcu host' $PB/printer_data/config/printer.cfg && grep -qx klipper_mcu $ROOT/config/moonraker.asvc && [ -f $ROOT/docs/HOST_MCU.md ]"
check "host MCU: --update runs the step too, and --dry-run only says what it would do" "inst $PB --dry-run --update | grep -q 'Step 7b' || inst $PB --dry-run --update | grep -qi 'host mcu'"
OUT="$(inst "$PB" --update)"
check "pi update shows its bar from 0 to 100 percent" "echo \"$OUT\" | grep -q 'Update step 1 of 8' && echo \"$OUT\" | grep -q '100%  Update finished'"
OUT="$(WM_HOME=$T/pb2 WM_TEST_SERVICES='makerbase-client klipper' WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $SB --pi 192.0.2.10 --no-reboot 2>&1 </dev/null)"
check "board install: bar from step 1 of 7 to 100 percent" "echo \"$OUT\" | grep -q 'Install step 1 of 7' && echo \"$OUT\" | grep -q 'Install step 7 of 7' && echo \"$OUT\" | grep -q '100%  All 7 steps finished'"

sec "== board update page and reboot question"
UP="$T/upn"; mkdir -p "$UP/zr_tools" "$UP/scripts"; echo 99.0.0 > "$UP/VERSION"; printf '# Changelog\n\n## 99.0.0\n\n- brand new thing\n\n## %s\n\n- old thing\n' "$(cat $ROOT/VERSION)" > "$UP/CHANGELOG.md"
UPH="$T/uph"; mkdir -p "$UPH"
check "board --check-updates lists what is new and stops at the installed version" "O=\$(WM_TEST_UPDATE_DIR=$UP WM_HOME=$UPH WM_INSTALLER_TEST=1 bash $SB --check-updates 2>&1 </dev/null); echo \"\$O\" | grep -q 'brand new thing' && ! echo \"\$O\" | grep -q 'old thing' && echo \"\$O\" | grep -q 'Newest: 99.0.0'"
check "board menu: Update page has See what is new and Update now" "mb '2\n0\n0\n' --menu | grep -q 'See what is new' && mb '2\n0\n0\n' --menu | grep -q 'Update now'"
RB="$T/rbq"; mkdir -p "$RB"
check "board install asks before rebooting; yes reboots" "WM_ASSUME_YES=1 WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$RB WM_INSTALLER_TEST=1 bash $SB --pi 192.0.2.10 </dev/null 2>&1 | grep -q 'Reboot the board now' || grep -q 'systemctl reboot' $RB/.sudo.log"
check "board install: the reboot is in the log when the answer is the default (yes)" "grep -q 'systemctl reboot' $RB/.sudo.log"
check "board install: --no-reboot asks nothing and does not reboot" "! WM_ASSUME_YES=1 WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$T/rbq2 WM_INSTALLER_TEST=1 bash $SB --pi 192.0.2.10 --no-reboot </dev/null 2>&1 | grep -q 'Reboot the board now'"

check "board factory restore shows its bar from step 1 of 3 to 100 percent" "O=\$(WM_ASSUME_YES=1 WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$T/fr WM_INSTALLER_TEST=1 bash $SB --pi 192.0.2.10 --no-reboot 2>&1 </dev/null >/dev/null; WM_ASSUME_YES=1 WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$T/fr WM_INSTALLER_TEST=1 bash $SB --factory-restore --no-reboot 2>&1 </dev/null); echo \"\$O\" | grep -q 'Factory restore step 1 of 3' && echo \"\$O\" | grep -q 'Factory restore step 2 of 3' && echo \"\$O\" | grep -q '100%  Factory restore finished'"

RFD="$T/wm_ultra_vanilla_klipper-board"; rm -rf "$RFD"; mkdir -p "$RFD/scripts" "$T/rfh"; cp "$SB" "$ROOT/scripts/lib_free_space.sh" "$RFD/scripts/"; echo 1.0.0 > "$RFD/VERSION"; mkdir -p "$T/rfn/zr_tools" "$T/rfn/scripts"; echo 99.0.0 > "$T/rfn/VERSION"; echo x > "$T/rfn/NEWFILE"; for f in zr_tools zr_views zr_logic pi_address_panel; do echo n > "$T/rfn/zr_tools/$f.py"; done; cp "$SB" "$T/rfn/scripts/"
check "board --update also refreshes the installer folder itself (so the menu shows the new version)" "WM_TEST_REFRESH=1 WM_ASSUME_YES=1 WM_TEST_UPDATE_DIR=$T/rfn WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$T/rfh WM_INSTALLER_TEST=1 bash $RFD/scripts/screen_board.sh --pi 192.0.2.10 --no-reboot >/dev/null 2>&1 </dev/null; WM_TEST_REFRESH=1 WM_ASSUME_YES=1 WM_TEST_UPDATE_DIR=$T/rfn WM_HOME=$T/rfh WM_INSTALLER_TEST=1 bash $RFD/scripts/screen_board.sh --update </dev/null 2>&1 | grep -q 'Updated to 99.0.0' && grep -q 99.0.0 $RFD/VERSION && [ -f $RFD/NEWFILE ]"

RUF="$T/ruf"; rm -rf "$RUF"; mkdir -p "$RUF/scripts" "$RUF/zr_tools"; cp "$SB" "$ROOT/scripts/lib_free_space.sh" "$RUF/scripts/"; echo 1.0.0 > "$RUF/VERSION"; RUH="$T/ruh"; mkdir -p "$RUH/printer_data/config" "$RUH/KlipperScreen/panels"
echo "[x]" > "$RUH/printer_data/config/KlipperScreen.conf"
check "board --update also refreshes the installer folder it runs from" "WM_TEST_REFRESH_REPO=1 WM_ASSUME_YES=1 WM_TEST_UPDATE_DIR=$UP WM_HOME=$RUH WM_INSTALLER_TEST=1 bash $RUF/scripts/screen_board.sh --update </dev/null 2>&1 | grep -q 'Updated to 99.0.0' && grep -q 99.0.0 $RUF/VERSION"

sec "== klipper restart after install and update"
KR="$T/kr"; mkstage "$T/stage_kr"; mkdir -p "$KR"; inst "$KR" --from-stage "$T/stage_kr" --screen off >/dev/null
: > "$KR/.sudo.log"; touch "$KR/.svc/klipper.active"
OUT="$(inst "$KR" --update)"
check "update restarts klipper at the end when it is running" "echo \"$OUT\" | grep -q 'Restarting Klipper' && [ \$(grep -c 'restart klipper' $KR/.sudo.log) -ge 1 ]"
rm -f "$KR/.svc/klipper.active"; : > "$KR/.sudo.log"
OUT="$(inst "$KR" --update)"
check "update does not start klipper when it is off (first start does that)" "echo \"$OUT\" | grep -q 'Klipper is not running, so it was not restarted' && ! grep -q 'restart klipper' $KR/.sudo.log"
check "update --dry-run restarts nothing" "touch $KR/.svc/klipper.active; : > $KR/.sudo.log; inst $KR --update --dry-run >/dev/null; ! grep -q 'restart klipper' $KR/.sudo.log"
BK2="$T/bk2"; mkdir -p "$BK2"
check "board install restarts klipper on the Pi through moonraker" "WM_ASSUME_YES=1 WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$BK2 WM_INSTALLER_TEST=1 bash $SB --pi 192.0.2.10 --no-reboot </dev/null 2>&1 | grep -q 'Klipper on the Pi restarted' && grep -q 'restart klipper on 192.0.2.10 via moonraker' $BK2/.sudo.log && grep -q 'restart KlipperScreen' $BK2/.sudo.log"
: > "$BK2/.sudo.log"
check "board update restarts klipper on the Pi and KlipperScreen" "WM_TEST_UPDATE_DIR=$UPD WM_ASSUME_YES=1 WM_HOME=$BK2 WM_INSTALLER_TEST=1 bash $SB --update </dev/null 2>&1 | grep -q 'Klipper on the Pi restarted' && grep -q 'restart klipper on' $BK2/.sudo.log && grep -q 'restart KlipperScreen' $BK2/.sudo.log"
check "board --dry-run restarts nothing on the Pi" "WM_ASSUME_YES=1 WM_HOME=$T/bk3 WM_INSTALLER_TEST=1 bash $SB --pi 192.0.2.10 --dry-run </dev/null 2>&1 | grep -qv 'Klipper on the Pi restarted'"

sec "== bars: weights, update, uninstall; doctor waits and re-checks"
check "pi install: bar percent grows and never goes backwards" "echo \"$(inst $T/pbw --from-github --model ultra-s)\" | grep -o '[0-9]*%' | tr -d '%' | awk 'NR>1 && \$1<prev {bad=1} {prev=\$1} END{exit bad}'"
PW="$T/pw"; rm -rf "$PW"; mkdir -p "$PW/KlipperScreen/panels" "$PW/printer_data/config"; echo "[x]" > "$PW/printer_data/config/KlipperScreen.conf"
check "board update shows its bar from 0 to 100 percent" "O=\$(WM_TEST_UPDATE_DIR=$UPD WM_ASSUME_YES=1 WM_HOME=$PW WM_INSTALLER_TEST=1 bash $SB --update </dev/null 2>&1); echo \"\$O\" | grep -q 'Update step 1 of 6' && echo \"\$O\" | grep -q '100%  Update finished'"
check "board doctor says how many problems were fixed" "WM_ASSUME_YES=1 WM_TEST_SERVICES='makerbase-client klipper' WM_HOME=$PW WM_INSTALLER_TEST=1 bash $SB --pi 192.0.2.10 --no-reboot </dev/null >/dev/null 2>&1; rm -f $PW/.svc/KlipperScreen.active; O=\$(WM_ASSUME_YES=1 WM_HOME=$PW WM_INSTALLER_TEST=1 bash $SB --doctor </dev/null 2>&1); echo \"\$O\" | grep -q 'KlipperScreen is not running' && echo \"\$O\" | grep -q 'fixed'"
UB="$T/ub"; mkdir -p "$UB/printer_data/config"; touch "$UB/Spoolman" 2>/dev/null; rm -f "$UB/Spoolman"; mkdir -p "$UB/Spoolman"
OUT="$(printf 'y\nn\n' | WM_HOME=$UB WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --remove spoolman 2>&1)"
check "single removal shows a bar that ends at 100 percent" "echo \"$OUT\" | grep -q '100%  spoolman removed' && echo \"$OUT\" | grep -q 'Removing the files'"
check "board --remove installer files show a bar at 100 percent" "mkdir -p $T/wm_ultra_vanilla_klipper-pb/scripts && cp $SB $ROOT/scripts/lib_free_space.sh $T/wm_ultra_vanilla_klipper-pb/scripts/ && echo 1 > $T/wm_ultra_vanilla_klipper-pb/VERSION && WM_ASSUME_YES=1 WM_HOME=$PW WM_INSTALLER_TEST=1 bash $T/wm_ultra_vanilla_klipper-pb/scripts/screen_board.sh --remove installer </dev/null 2>&1 | grep -q '100%  Done'"


echo "Progress bar never gets in the way of a question"
bar_check() {   # script-with-progress_bar : the bar is printed once, never redrawn, and no background job is started
    local LB; LB="$(mktemp -d)"
    cat > "$LB/lt.sh" <<EOT
GREEN=; NC=; TESTING=0; DRY=0
eval "\$(sed -n '/^prog_repeat()/p;/^progress_bar()/,/^}/p' $1)"
progress_bar 1 5 "Step 2 of 5"; read -r -p "question? " a; echo "[\$a]"; sleep 2; jobs -p | wc -l
EOT
    python3 - "$LB/lt.sh" <<'EOP'
import pty,os,struct,fcntl,termios,time,sys
pid,fd=pty.fork()
if pid==0: os.execvp('bash',['bash',sys.argv[1]])
fcntl.ioctl(fd,termios.TIOCSWINSZ,struct.pack('HHHH',24,80,0,0))
out=b''; t=time.time(); sent=False
while time.time()-t<6:
    try: d=os.read(fd,4096)
    except OSError: break
    if not d: break
    out+=d
    if b'question?' in out and not sent: time.sleep(1.2); os.write(fd,b'hello\n'); sent=True
sys.exit(0 if out.count(b'Step 2 of 5')==1 and b'\x1b[' not in out.replace(b'\x1b[0m',b'').replace(b'\x1b[0;32m',b'') and b'[hello]' in out and b'\n0' in out.replace(b'\r',b'') else 1)
EOP
}
check "Pi installer: the bar is printed once and a question after it stays clean" "bar_check $ROOT/installer.sh"
check "screen board: the bar is printed once and a question after it stays clean" "bar_check $ROOT/scripts/screen_board.sh"
check "bars: Check, Doctor, support bundle and backup all end at 100 percent" "M '' $LG --check | grep -q '100%  Check finished' && M '' $LG --doctor | grep -q '100%  Doctor finished' && M '' $LG --support-bundle | grep -q '100%  Done' && M '' $LG --backup | grep -q '100%  Done'"
# ---- PID settings where SAVE_CONFIG can store them (scripts/wm_pidcfg.py, installer step 4d, --pid-cfg, Doctor)
G3="$T/g3"; rm -rf "$G3"; mkdir -p "$G3/printer_data"; cp -r "$ROOT/factory/ultra-s/config" "$G3/printer_data/config"; echo ultra-s > "$G3/printer_data/wm-model"
P3="$G3/printer_data/config"
cp "$ROOT/tests/fixtures/printer_wm_style.cfg" "$P3/printer.cfg"   # a printer.cfg in the layout WonderMaker ships (PID only saved for the first hotend)
check "pid-cfg: the check ignores the chamber heater (zru-s.cfg keeps its control and PID, see chamber_test/README.md)" "grep -q '^pid_Kp=63.418' $P3/zru-s.cfg && ! python3 $ROOT/scripts/wm_pidcfg.py check $P3 | grep -qi 'chamber\|CONFLICT'"
check "pid-cfg: the printer.cfg of this repository already has control: pid for every hotend and the bed" "python3 $ROOT/scripts/wm_pidcfg.py check $ROOT/factory/ultra-s/config | grep -qx OK && python3 $ROOT/scripts/wm_pidcfg.py check $ROOT/factory/ultra/config | grep -qx OK"
check "pid-cfg: the factory file saves PID only for the first hotend, so the check finds the other three (the installer fixes them)" "python3 $ROOT/scripts/wm_pidcfg.py check $P3 | grep -c '^HOTEND' | grep -qx 3"
D3="WM_HOME=$G3 WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh"
DR3="yes n 2>/dev/null | WM_HOME=$G3 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor"   # answers n to every fix: report only
check "doctor reports the hotends without PID and not the chamber (and changes nothing when the fix is declined)" "eval \"$DR3\" > $T/dr1.out 2>&1; grep -q 'problem.*PID settings: HOTEND' $T/dr1.out && ! grep -q 'PID settings:.*CONFLICT' $T/dr1.out && grep -q '^pid_Kp=63.418' $P3/zru-s.cfg"
WM_HOME="$G3" WM_INSTALLER_TEST=1 bash "$ROOT/installer.sh" --pid-cfg --dry-run >/dev/null 2>&1 </dev/null
check "--pid-cfg dry run changes nothing" "grep -q '^pid_Kp=63.418' $P3/zru-s.cfg && ! ls $P3/*.wm-before-pidcfg-* "
WM_HOME="$G3" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --pid-cfg > "$T/pid.out" 2>&1 </dev/null
check "--pid-cfg leaves the chamber heater alone: zru-s.cfg keeps its PID and printer.cfg gets no chamber section" "grep -q '^pid_Kp=63.418' $P3/zru-s.cfg && ! grep -q '^\\[heater_generic chamber\\]' $P3/printer.cfg"
check "--pid-cfg does not change zru-s.cfg at all" "cmp $P3/zru-s.cfg $ROOT/factory/ultra-s/config/zru-s.cfg"
check "--pid-cfg keeps a copy of printer.cfg and makes none of zru-s.cfg" "ls $P3/printer.cfg.wm-before-pidcfg-* >/dev/null && ! ls $P3/zru-s.cfg.wm-before-pidcfg-* 2>/dev/null"
check "--pid-cfg leaves the SAVE_CONFIG block alone" "diff <(sed -n '/SAVE_CONFIG ---/,\$p' $ROOT/tests/fixtures/printer_wm_style.cfg) <(sed -n '/SAVE_CONFIG ---/,\$p' $P3/printer.cfg)"
check "the pid check is clean after the fix" "python3 $ROOT/scripts/wm_pidcfg.py check $P3 | grep -qx OK"
NBP=$(ls $P3 | grep -c 'wm-before-pidcfg')
WM_HOME="$G3" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --pid-cfg > "$T/pid2.out" 2>&1 </dev/null
check "--pid-cfg is idempotent: second run says fine and makes no new copy" "grep -q 'PID settings are where SAVE_CONFIG can store them' $T/pid2.out && [ \$(ls $P3 | grep -c 'wm-before-pidcfg') = $NBP ]"
check "doctor is happy after the fix" "$D3 --doctor 2>&1 </dev/null | grep -q 'ok.*PID settings of the hotends and the bed'"
python3 - "$P3/printer.cfg" <<'PY'
import re,sys
f=sys.argv[1]; s=open(f).read()
s=re.sub(r"#\*# \[extruder\d?\]\n(#\*# (control|pid_k.) = .*\n)+#\*#\n","",s)
open(f,"w").write(s)
PY
check "pid-cfg: hotends without control: pid and without a saved value are found" "python3 $ROOT/scripts/wm_pidcfg.py check $P3 | grep -c '^HOTEND' | grep -qx 1"
cp "$P3/printer.cfg" "$T/pid-before.cfg"
WM_HOME="$G3" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" --doctor --fix-all >/dev/null 2>&1 </dev/null
check "Fix everything gives the 4 hotends control: pid (5 lines with the bed) and keeps their old (commented) values" "[ \$(sed -n '1,/SAVE_CONFIG ---/p' $P3/printer.cfg | grep -c '^control: pid') = 5 ] && grep -q '^pid_Kp: 25.788' $P3/printer.cfg && grep -q '^pid_Kd: 14.291' $P3/printer.cfg"
check "pid check is clean again (hotends and bed)" "python3 $ROOT/scripts/wm_pidcfg.py check $P3 | grep -qx OK"
check "the hotend fix saved printer.cfg first" "ls $P3/printer.cfg.wm-before-pidcfg-* >/dev/null && grep -q '^#control: pid' $P3/printer.cfg.wm-before-pidcfg-*"
check "the Ultra (no zru-s.cfg include, no chamber) is not touched" "R=$T/g4; rm -rf \$R; mkdir -p \$R/printer_data; cp -r $ROOT/factory/ultra/config \$R/printer_data/config; ! grep -q 'heater_generic chamber' \$R/printer_data/config/printer.cfg && ! grep -q '^\\[include zru-s.cfg\\]' \$R/printer_data/config/printer.cfg"
check "chamber_test: the README and the old script are kept, and the old script still finds the chamber conflict" "[ -s $ROOT/chamber_test/README.md ] && R=$T/g6; rm -rf \$R; mkdir -p \$R; cp -r $ROOT/factory/ultra-s/config \$R/config; python3 $ROOT/chamber_test/wm_pidcfg_with_chamber.py check \$R/config | grep -q 'CONFLICT zru-s.cfg \\[heater_generic chamber\\] control pid_Kp pid_Ki pid_Kd'"
# ---- 2.11.0: the main board fan is renamed motherboard_fan -> MCU_fan (Fluidd shows "MCU Fan")
check "fan rename: every factory printer.cfg has [controller_fan MCU_fan] and no motherboard_fan" "(for f in $ROOT/factory/*/config/printer.cfg $ROOT/factory/*/config-variants/printer?.cfg; do grep -q '^\[controller_fan MCU_fan\]' \$f && ! grep -q 'motherboard_fan' \$f || exit 1; done)"
check "fan rename at update: an untouched or a changed fan section is renamed (own values kept), never there twice" "python3 -I - $ROOT/scripts/wm_cfgmerge.py <<'PY'
import importlib.util, sys
sp = importlib.util.spec_from_file_location('m', sys.argv[1]); m = importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
base = '[printer]\nmax_velocity: 300\n\n[controller_fan motherboard_fan]\npin:PA8\nmax_power:0.5\n'
rel = base.replace('motherboard_fan', 'MCU_fan')
for live in (base, base.replace('max_power:0.5', 'max_power:0.7')):
    mm = m.merge(base, rel, live); out = m.render(mm, [])
    assert out.count('[controller_fan') == 1 and '[controller_fan MCU_fan]' in out and 'motherboard_fan' not in out, out
    assert ('max_power:0.7' in out) == ('max_power:0.7' in live), out
PY"

# ---- WonderMaker's printer.cfg changes merged into the Pi's printer.cfg (scripts/wm_cfgmerge.py, installer step 4e, --cfg-merge)
check "doctor says when the WonderMaker printer.cfg starting point is not recorded" "grep -q 'problem.*printer.cfg this Pi was set up from is not recorded' $T/dr1.out"
RP="$T/repo5"; rm -rf "$RP"; mkdir -p "$RP/factory/ultra-s/config" "$RP/scripts" "$RP/rpi-cfg"; cp "$ROOT/installer.sh" "$ROOT/VERSION" "$RP/"; cp "$ROOT"/scripts/* "$RP/scripts/"; cp "$ROOT"/rpi-cfg/* "$RP/rpi-cfg/"
cp "$ROOT/factory/ultra-s/config/printer.cfg" "$T/pc-old.cfg"
python3 - "$T/pc-old.cfg" "$RP/factory/ultra-s/config/printer.cfg" <<'PY'
import sys
s=open(sys.argv[1]).read()
n=s.replace("pressure_advance: 0.032","pressure_advance: 0.040",1).replace("max_extrude_cross_section:5000","max_extrude_cross_section:6000",1)
n=n.replace("#*# <---------------------- SAVE_CONFIG","[output_pin wm_new_pin]\npin: PB9\n\n#*# <---------------------- SAVE_CONFIG",1)
open(sys.argv[2],"w").write(n)
PY
G5="$T/g5"; rm -rf "$G5"; mkdir -p "$G5/printer_data"; cp -r "$ROOT/factory/ultra-s/config" "$G5/printer_data/config"; echo ultra-s > "$G5/printer_data/wm-model"; P5="$G5/printer_data/config"
python3 "$ROOT/scripts/wm_pidcfg.py" fix "$P5" T0 >/dev/null; rm -f "$P5"/*.wm-before-pidcfg-*   # a Pi whose PID settings are already fine
sed -i 's/^pressure_advance: 0.032/pressure_advance: 0.045/; s/^#\*# pid_kp = 26.638/#*# pid_kp = 99.999/' "$P5/printer.cfg"
sed -i 's|^#\*# <---------------------- SAVE_CONFIG|[output_pin my_led]\npin: PB1\n\n&|' "$P5/printer.cfg"
sed -i '1i [include rpi_calibration.cfg]' "$P5/printer.cfg"
cp "$P5/printer.cfg" "$T/pc5.mine"
WM_HOME="$G5" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$RP/installer.sh" --cfg-merge > "$T/cm0.out" 2>&1 </dev/null
check "--cfg-merge with no record only records the starting point and changes nothing" "cmp $P5/printer.cfg $T/pc5.mine && cmp $G5/printer_data/wm-baseline/printer.cfg $RP/factory/ultra-s/config/printer.cfg && grep -q 'Recorded this repository' $T/cm0.out"
cp "$T/pc-old.cfg" "$G5/printer_data/wm-baseline/printer.cfg"   # the Pi was set up from the old WonderMaker file
WM_HOME="$G5" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$RP/installer.sh" --cfg-merge --dry-run >/dev/null 2>&1 </dev/null
check "--cfg-merge dry run changes nothing" "cmp $P5/printer.cfg $T/pc5.mine"
WM_HOME="$G5" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$RP/installer.sh" --cfg-merge > "$T/cm1.out" 2>&1 </dev/null
check "merge: WonderMaker's new setting and new section arrive" "grep -q '^max_extrude_cross_section:6000' $P5/printer.cfg && grep -q '^\\[output_pin wm_new_pin\\]' $P5/printer.cfg"
check "merge: my value (a conflict, assume-yes keeps mine), my section and my include stay" "grep -q '^pressure_advance: 0.045' $P5/printer.cfg && grep -q '^\\[output_pin my_led\\]' $P5/printer.cfg && head -1 $P5/printer.cfg | grep -qx '\\[include rpi_calibration.cfg\\]'"
check "merge: the SAVE_CONFIG block is mine, byte for byte" "diff <(sed -n '/SAVE_CONFIG ---/,\$p' $T/pc5.mine) <(sed -n '/SAVE_CONFIG ---/,\$p' $P5/printer.cfg)"
check "merge: a copy of my printer.cfg is kept and the starting point moves to the new version" "cmp $T/pc5.mine $P5/printer.cfg.wm-before-cfgmerge-* && cmp $G5/printer_data/wm-baseline/printer.cfg $RP/factory/ultra-s/config/printer.cfg"
NBC=$(ls $P5 | grep -c 'wm-before-cfgmerge')
WM_HOME="$G5" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$RP/installer.sh" --cfg-merge > "$T/cm2.out" 2>&1 </dev/null
check "merge: a second run finds nothing to do and makes no new copy" "grep -q 'already has everything' $T/cm2.out && [ \$(ls $P5 | grep -c 'wm-before-cfgmerge') = $NBC ]"
check "the merge keeps the PID settings in a place SAVE_CONFIG can store them" "python3 $ROOT/scripts/wm_pidcfg.py check $P5 | grep -qx OK || python3 $ROOT/scripts/wm_pidcfg.py check $P5 | grep -q CONFLICT"
check "backup and auto backup include the recorded starting point" "[ \$(grep -c 'printer_data/wm-baseline' $ROOT/installer.sh) -ge 3 ]"
python3 - "$ROOT/scripts/wm_cfgmerge.py" <<'PY'
import importlib.util,sys
sp=importlib.util.spec_from_file_location("m",sys.argv[1]); m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m)
base="[mcu T0]\ncanbus_uuid: aaaa\n[extruder]\nrotation_distance: 21.0\n"
rel="[mcu T0]\ncanbus_uuid: bbbb\n[extruder]\nrotation_distance: 22.0\nnew_opt: 1\n[gone]\nx: 1\n"
live="[mcu T0]\ncanbus_uuid: cccc\n[extruder]\nrotation_distance: 21.0\nmy_opt: 2\n"
t,c,n=m.merge_cfg(base,rel,live)
ok = "canbus_uuid: cccc" in t and "bbbb" not in t and "rotation_distance: 22.0" in t and "new_opt: 1" in t and "my_opt: 2" in t and not c
sys.exit(0 if ok else 1)
PY
check "merge unit: canbus_uuid stays the Pi's, WonderMaker's change and new setting arrive, my setting stays" "[ $? = 0 ]"
check "pip is told not to check for a newer pip (no warning on slow links)" "grep -q '^export PIP_DISABLE_PIP_VERSION_CHECK=1' $ROOT/installer.sh && grep -q '^export PIP_DISABLE_PIP_VERSION_CHECK=1' $ROOT/scripts/screen_board.sh"
check "board update: waits at most 60 s for Klipper on the Pi, says it is still waiting, and cleans /tmp on Ctrl-C" "grep -q 'still waiting: Klipper on the Pi' $ROOT/scripts/screen_board.sh && grep -q 'rm -rf \"\${LATEST_TMP:-}\"; exit 130' $ROOT/scripts/screen_board.sh && ! grep -q 'for i in \$(seq 1 30); do' <(sed -n '/^restart_pi_klipper/,/^}/p' $ROOT/scripts/screen_board.sh)"
check "board lib error message names an option that exists" "! grep -q 'screen_board.sh --get-latest' $ROOT/scripts/screen_board.sh"
check "Pi installer: Klipper wait prints progress; the download in /tmp is removed on Ctrl-C" "grep -q 'still waiting: Klipper is' $ROOT/installer.sh && grep -q \"trap '_rmw; exit 130' INT TERM\" $ROOT/installer.sh"
check "dev box: tool and simulation unit tests" "python3 -I -W ignore $ROOT/tests/test_devbox.py"
check "dev box: the README has no banner and links the tool" "! head -3 $ROOT/README.md | grep -qi 'dev box branch' && grep -q 'tools/devbox/' $ROOT/README.md && [ -f $ROOT/README-DEVBOX.md ]"
DBH="$T/dbh"; mkdir -p "$DBH/printer_data/config" "$DBH/printer_data/systemd"; cp "$ROOT/factory/ultra-s/config/printer.cfg" "$DBH/printer_data/config/"
check "dev box: no notice from the Doctor, --cfg-merge or --pid-cfg while it is off" "! (yes n | WM_HOME=$DBH WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1; WM_HOME=$DBH WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --pid-cfg 2>&1 </dev/null) | grep -q 'Dev box mode is ON'"
echo 'KLIPPER_ARGS="/k/klippy.py '"$DBH"'/printer_data/devbox/config/printer.cfg -I /c/klippy.serial"' > "$DBH/printer_data/systemd/klipper.env"
check "dev box: the Doctor says dev mode is on" "yes n | WM_HOME=$DBH WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --doctor 2>&1 | grep -q 'Dev box mode is ON'"
check "dev box: --pid-cfg and --cfg-merge say it too" "WM_HOME=$DBH WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --pid-cfg 2>&1 </dev/null | grep -q 'Dev box mode is ON' && WM_HOME=$DBH WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash $ROOT/installer.sh --cfg-merge 2>&1 </dev/null | grep -q 'Dev box mode is ON'"

sec "== vanilla Klipper and Moonraker (wm_ultra_vanilla_klipper)"
if [ -d "$ROOT/.git" ]; then
for m in ultra ultra-s; do
check "$m: every file in SHA256SUMS and modules.sha256 is tracked by git (the bundled Klipper's .gitignore hides *.so)" "cd $ROOT && ! (awk '{print \"factory/$m/\" \$2}' factory/$m/SHA256SUMS; awk '{print \"factory/$m/klipper/\" \$2}' factory/$m/modules.sha256) | sort -u | comm -23 - <(git ls-files | sort) | grep -q ."
done
fi
for m in ultra ultra-s; do
check "$m: Klipper is the pinned upstream tree (COPYING, klippy.py, lib/) with the Pi-side modules" "[ -f $ROOT/factory/$m/klipper/COPYING ] && [ -f $ROOT/factory/$m/klipper/klippy/klippy.py ] && [ -d $ROOT/factory/$m/klipper/lib ] && for f in wm_adaptive_mesh wm_mcu_tweaks wm_pin_pulse wm_stepper_diag wm_gcode_compat wm_ready_compat; do [ -f $ROOT/factory/$m/klipper/klippy/extras/\$f.py ] || exit 1; done"
check "$m: WonderMaker's 5 compiled modules are the factory files (modules.sha256)" "(cd $ROOT/factory/$m/klipper && sha256sum -c ../modules.sha256)"
check "$m: no ACE Pro files and no shell-command module in the bundled Klipper (installed on request / by their steps)" "[ ! -e $ROOT/factory/$m/klipper/klippy/extras/ace ] && [ ! -e $ROOT/factory/$m/klipper/klippy/extras/temperature_ace.py ] && [ ! -e $ROOT/factory/$m/klipper/klippy/extras/virtual_pins.py ] && [ ! -e $ROOT/factory/$m/klipper/klippy/extras/gcode_shell_command.py ]"
check "$m: Moonraker is the upstream tree" "[ -f $ROOT/factory/$m/moonraker/moonraker/moonraker.py ] && [ -f $ROOT/factory/$m/moonraker/LICENSE ]"
check "$m: clean start: z_offset 0 in printer.cfg, an empty SAVE_CONFIG block, tool offsets 0" "grep -q '^z_offset:0' $ROOT/factory/$m/config/printer.cfg && [ \$(sed -n '/SAVE_CONFIG ---/,\$p' $ROOT/factory/$m/config/printer.cfg | grep -c '^#\*# [a-z]') = 0 ] && ! grep -v '(0.0, 0.0, 0.0)' $ROOT/factory/$m/config/saved_variables.cfg | grep -q '^t[0-3]_offset'"
check "$m: the Pi's own include lines are left to the installer" "! grep -qE '^\[include (rpi_pi|zr_tools|rpi_nozzle|rpi_calibration|rpi_ace|rpi_ace_driver|rpi_endless|rpi_stats|test_macro)\.cfg\]' $ROOT/factory/$m/config/printer.cfg"
check "$m: no private address and no real CAN id of one printer in the config" "! grep -rIE '10\.11\.88\.|ac8b57e80210|aa157497ce9c' $ROOT/factory/$m/config"
done
check "requirements are the exact lists of the tested Pi (Klipper 3.9 list, Moonraker list)" "grep -q '^msgspec==0.19.0' $ROOT/config/klippy-requirements.txt && grep -q '^dbus-fast==' $ROOT/config/moonraker-requirements.txt && ! grep -qi 'wonderMaker' $ROOT/config/klippy-requirements.txt"
check "Moonraker's environment is built with the system Python, Klipper's with Python 3.9" "grep -q 'python3 -m venv \"\$HOME_DIR/moonraker-env\"' $ROOT/installer.sh && grep -q '\"\$PY39\" -m venv \"\$HOME_DIR/klippy-env\"' $ROOT/installer.sh"
check "--version names this project, VERSION is 2.x" "bash $ROOT/installer.sh --version | grep -q 'wm_ultra_vanilla_klipper installer 2\\.' && grep -q '^2\\.' $ROOT/VERSION"
check "the install starts the services last: board sensors come before do_first_start auto; the Fluidd categories follow it (Klipper must run for them) and come before Done" "l(){ grep -n \"\$1\" $ROOT/installer.sh | tail -1 | cut -d: -f1; }; a=\$(l '^step_fluidd_categories   # again'); b=\$(l '^pi_sensors_in_flow\$'); c=\$(l 'do_first_start auto || true'); d=\$(l '^print_header \"Done\"'); [ -n \"\$a\" ] && [ \"\$b\" -lt \"\$c\" ] && [ \"\$c\" -lt \"\$a\" ] && [ \"\$a\" -lt \"\$d\" ]"
check "the install flow adds the board sensors and host MCU without a Klipper restart when Klipper is not running yet (--pi-sensors alone still needs Klipper)" "grep -q 'Klipper loads it when it starts' $ROOT/installer.sh && grep -q 'PISENS_INSTALL=1 step_pi_sensors' $ROOT/installer.sh && grep -q 'PISENS_INSTALL:-0}\" != 1' $ROOT/installer.sh"
check "the first-start CAN check asks up to 3 times (the bus needs a moment after can0 comes up)" "grep -q 'found=\"\$(found_uuids_retry)\"' $ROOT/installer.sh"
check "README: OrcaSlicer section, its three screenshots exist, and every README image link points to a file" "grep -q '^### 4.2 Slicer: use OrcaSlicer' $ROOT/README.md && for f in start-end timelapse pause; do [ -s $ROOT/docs/img/orca-machine-gcode-\$f.png ] || exit 1; done; for i in \$(grep -o 'docs/img/[A-Za-z0-9_.-]*' $ROOT/README.md | sort -u); do [ -s $ROOT/\$i ] || { echo missing \$i; exit 1; }; done"
check "first start fails (not 'all checks passed') while a board still has a placeholder CAN id" "grep -q 'still have a placeholder CAN id, so Klipper cannot connect to them' $ROOT/installer.sh"
check "Fluidd macro categories are only reported as set up when Moonraker's database holds them" "grep -q 'namespace=fluidd&key=macros\" | grep -q .\"stored.' $ROOT/installer.sh"
check "--help no longer lists --modules" "! bash $ROOT/installer.sh --help | grep -q -- '--modules'"
RW="$T/rw1"; rm -rf "$RW"; mkdir -p "$RW/wm-rpi-backup"; printf 'VERSION=1.23.71\n' > "$RW/wm-rpi-backup/install.conf"
check "a Pi with a wm-ultra-rpi install record is refused before anything changes" "! inst $RW --from-github --model ultra-s >$T/rw1.out 2>&1; grep -q 'already runs WonderMaker' $T/rw1.out && [ ! -d $RW/klipper ] && [ ! -d $RW/printer_data ]"
RW2="$T/rw2"; rm -rf "$RW2"; mkdir -p "$RW2/klipper/klippy"; echo x > "$RW2/klipper/klippy/klippy.py"
check "a Pi with WonderMaker's own Klipper is refused, nothing is moved" "! inst $RW2 --from-github --model ultra-s >$T/rw2.out 2>&1; grep -q 'not the Klipper this installer sets up' $T/rw2.out && [ -f $RW2/klipper/klippy/klippy.py ] && [ ! -d $RW2/wm-rpi-backup/old-* ]"
RW3="$T/rw3"; rm -rf "$RW3"; mkdir -p "$RW3/klipper/klippy/extras"; echo x > "$RW3/klipper/klippy/klippy.py"; echo x > "$RW3/klipper/klippy/extras/wm_mcu_tweaks.py"
check "a Pi that already has this installer's Klipper is not refused (a reinstall moves the old folders aside)" "inst $RW3 --from-github --model ultra-s --dry-run >$T/rw3.out 2>&1; ! grep -q 'already runs WonderMaker' $T/rw3.out"
for m in ultra ultra-s; do check "$m: RESUME prints \"Print resumed\" and hands feed assist back to the watcher (ACE only)" "grep -q 'RESPOND MSG=\"Print resumed\"' $ROOT/factory/$m/config/macros.cfg && grep -q 'VARIABLE=manual VALUE=-2' $ROOT/factory/$m/config/macros.cfg"; done
sec "== load cell board (CELL): firmware V2 from wm-load-cell-mcu"
CS="$T/cellstub"; rm -rf "$CS"; mkdir -p "$CS/zr-ultra/firmware"; echo 'echo menu' > "$CS/install.sh"; echo 'echo flash' > "$CS/zr-ultra/2_flash_app_can.sh"; echo KLP_CELL_WM_ZRU_RPI_V2_20261117 > "$CS/zr-ultra/firmware/LATEST"
cellinst() { local h="$1" v="$2"; shift 2; WM_TEST_CELL_DIR="$CS" WM_TEST_CELL_VERSION="$v" WM_TEST_PANEL_DIR="$T/stubpanel" WM_HOME="$h" WM_INSTALLER_TEST=1 WM_ASSUME_YES=1 bash "$ROOT/installer.sh" "$@" </dev/null 2>&1; }
CH="$T/cellh"; rm -rf "$CH"; mkdir -p "$CH"
check "load cell: --load-cell downloads the project and opens its menu" "cellinst $CH '' --load-cell > $CH.out; grep -q 'Load cell board' $CH.out && [ -f $CH/wm-load-cell-mcu/install.sh ] && grep -q 'load cell menu' $CH/.cell.log"
check "load cell: --load-cell says so when the project cannot be downloaded" "WM_HOME=$CH WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --load-cell </dev/null 2>&1 | grep -q 'Could not download'"
CI="$T/celli"; rm -rf "$CI"; mkdir -p "$CI"; mkstage "$T/stage"
OUTC="$(cellinst $CI KLP_CELL_WM_ZRU_20251223_162212 --from-stage $T/stage)"
check "load cell: an install on the factory firmware offers V2 but a run without questions does not flash and says how" "echo \"\$OUTC\" | grep -q 'Load cell board (CELL): firmware V2' && echo \"\$OUTC\" | grep -q 'NOT flashed' && echo \"\$OUTC\" | grep -q './installer.sh --load-cell' && [ ! -f $CI/.cell.log ]"
CJ="$T/cellj"; rm -rf "$CJ"; mkdir -p "$CJ"
check "load cell: a board already on V2 is left alone" "cellinst $CJ KLP_CELL_WM_ZRU_RPI_V2_20261117 --from-stage $T/stage | grep -q 'already runs KLP_CELL_WM_ZRU_RPI_V2_20261117'"
CK="$T/cellk"; rm -rf "$CK"; mkdir -p "$CK"
check "load cell: when Klipper does not answer for [mcu CELL] the install warns and goes on" "cellinst $CK '' --from-stage $T/stage | grep -q 'load cell board was not checked'"
CL="$T/cellL"; rm -rf "$CL"; mkdir -p "$CL"
check "load cell: --no-load-cell skips the whole step" "! cellinst $CL KLP_CELL_WM_ZRU_20251223_162212 --from-stage $T/stage --no-load-cell | grep -q 'Load cell board (CELL)'"
check "load cell: an update never touches the load cell board" "! cellinst $CI KLP_CELL_WM_ZRU_20251223_162212 --update --no-backup | grep -q 'Load cell board (CELL)'"
check "load cell: the step comes after the first start and before Done, and the Advanced menu has it" "l(){ grep -n \"\$1\" $ROOT/installer.sh | tail -1 | cut -d: -f1; }; a=\$(l 'do_first_start auto || true'); b=\$(l '^step_load_cell '); c=\$(l '^print_header \"Done\"'); [ \"\$a\" -lt \"\$b\" ] && [ \"\$b\" -lt \"\$c\" ] && grep -q 'menu_item 7 \"Load cell board\"' $ROOT/installer.sh && grep -q 'menu_run --load-cell' $ROOT/installer.sh"
check "load cell: --help lists --load-cell and --no-load-cell" "bash $ROOT/installer.sh --help | grep -q -- '--load-cell' && grep -q -- '--no-load-cell' $ROOT/installer.sh"

sec "== 2.20.1: state at the end, saved_variables temp file, Fluidd categories after start, ModemManager, doctor checks"
SH2="$T/sg2"; mkdir -p "$SH2/printer_data/config" "$SH2/printer_data/logs"; mksv "$SH2/printer_data/config/saved_variables.cfg"
for i in 1 2 3 4 5 6; do HOME="$SH2" bash "$ROOT/scripts/wm_sv_guard.sh" backup & done; wait
check "guard: six backups at the same moment leave no temp file and one good copy" "[ ! -e $SH2/printer_data/config/saved_variables.cfg.wm-good.tmp ] && ! ls $SH2/printer_data/config/saved_variables.cfg.wm-good.tmp.* >/dev/null 2>&1 && cmp -s $SH2/printer_data/config/saved_variables.cfg $SH2/printer_data/config/saved_variables.cfg.wm-good"
check "ModemManager rule: ACE Pro, MKS adapter and Klipper boards are ignored" "grep -q 'ATTRS{idVendor}==\"28e9\".*ID_MM_DEVICE_IGNORE' $ROOT/config/99-wm-no-modemmanager.rules && grep -q 'ATTRS{idVendor}==\"1d50\".*ID_MM_DEVICE_IGNORE' $ROOT/config/99-wm-no-modemmanager.rules && grep -q '99-wm-no-modemmanager.rules' $ROOT/installer.sh"
check "start: a first start in error/shutdown gets one firmware restart before it is reported" "grep -q 'normal after the board matching): restarting the firmware once' $ROOT/installer.sh"
check "start: the warning 'Klipper state after start' is dropped when Klipper is ready at the end" "grep -q 'Klipper state after start:\"\*) ;;' $ROOT/installer.sh"
check "Fluidd categories: run after the first start and the load cell step, not before Klipper runs" "l(){ grep -n \"\$1\" $ROOT/installer.sh | tail -1 | cut -d: -f1; }; a=\$(l '^step_load_cell   # after Klipper'); b=\$(l '^step_fluidd_categories   # again'); c=\$(l '^step_ultrabackup   # again'); [ \$a -lt \$b ] && [ \$b -lt \$c ] && ! grep -q '^step_fluidd_categories\$' $ROOT/installer.sh"
check "backups: swept again at the very end of an install" "grep -q '^step_ultrabackup   # again' $ROOT/installer.sh"
OUT="$(inst "$HR" --doctor)"
check "doctor: has the saved_variables safeguard, ModemManager and board matching checks" "echo \"$OUT\" | grep -q 'saved_variables safeguard' && echo \"$OUT\" | grep -q 'ModemManager is told' && echo \"$OUT\" | grep -q 'wm_canmatch.py'"
check "doctor: checks the Fluidd categories, Klipper state, ACE Pro on USB and the load cell firmware" "grep -q 'Fluidd macro categories are not set up' $ROOT/installer.sh && grep -q 'ACE Pro found on USB' $ROOT/installer.sh && grep -q 'load cell board: firmware V2' $ROOT/installer.sh && grep -q 'Klipper is ready\"' $ROOT/installer.sh"
PANEL_INST="${WM_PANEL_REPO:-/home/claude/wm-ultra-fluidd-acepro-panel}/installer.sh"
if [ -f "$PANEL_INST" ]; then check "panel: --fluidd-categories waits for Klipper" "grep -q 'fluiddcat) step_fluidd_categories 60' $PANEL_INST"; else echo "  skip panel: --fluidd-categories waits for Klipper (panel repository not on this machine, set WM_PANEL_REPO)"; fi

sec "== 2.20.1 (light watcher, F-142): chamber light by itself (wm-light.path), First Run Calibration without Extruder Setup"
check "light watcher: --light writes wm-light.path (watches rpi_chamber_light.json) and wm-light.service (--light --yes)" "grep -q 'PathChanged=.*printer_data/config/rpi_chamber_light.json' $G2/.wm-units/wm-light.path && grep -q 'Unit=wm-light.service' $G2/.wm-units/wm-light.path && grep -q 'installer.sh --light --yes' $G2/.wm-units/wm-light.service && grep -q 'Type=oneshot' $G2/.wm-units/wm-light.service"
check "light watcher: the dry run installs nothing" "rm -rf $G2/.wm-units; WM_HOME=$G2 WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --light --dry-run </dev/null 2>&1 | grep -q 'would install wm-light.path' && [ ! -e $G2/.wm-units/wm-light.path ]"
check "light watcher: the doctor checks it and the uninstall removes it" "grep -q 'wm-light.path is not running' $ROOT/installer.sh && grep -q 'systemctl disable wm-light.path' $ROOT/installer.sh"
check "first run calibration: no Extruder Setup stage, setter position stage first, no second Save and Restart" "! grep -q '_WM_FIRST_RUN_CAL_REST' $ROOT/rpi-cfg/rpi_calibration.cfg && ! grep -q 'WM_EXTRUDER_SETUP' <(sed -n '/gcode_macro _WM_FIRST_RUN_CAL\]/,/gcode_macro _WM_FIRST_RUN_CAL_DONE/p' $ROOT/rpi-cfg/rpi_calibration.cfg) && ! grep -q 'variable_full' $ROOT/rpi-cfg/rpi_nozzle.cfg"
check "first run calibration: the macros still render and behave" "python3 $ROOT/tests/rpi_cfg_render.py | tail -3 | grep -q 'macros render'"

sec "== 2.36.0: clean reinstall (WonderMaker files back to this version, machine files stay)"
mkstage "$T/clrstage"; CR="$T/clrhome"; rm -rf "$CR"; mkdir -p "$CR"
inst "$CR" --from-stage "$T/clrstage" --screen off >/dev/null
CRC="$CR/printer_data/config"; CRM="$(basename $(ls $ROOT/factory/*/config/macros.cfg | head -n1))"
for crf in macros.cfg change_macros.cfg rpi_base.cfg rpi_calibration.cfg; do [ -f "$CRC/$crf" ] || cp "$( [ -f $ROOT/rpi-cfg/$crf ] && echo $ROOT/rpi-cfg/$crf || ls $ROOT/factory/*/config/$crf | head -n1 )" "$CRC/$crf"; done
echo "[gcode_macro MY_OWN_EDIT]" >> "$CRC/macros.cfg"; echo "# my own comment" >> "$CRC/rpi_calibration.cfg"
for crf in printer.cfg saved_variables.cfg rpi_pi.cfg moonraker.conf KlipperScreen.conf; do [ -f "$CRC/$crf" ] || echo "# machine file $crf" > "$CRC/$crf"; echo "# my machine line" >> "$CRC/$crf"; done
CRALL0="$(cd $CRC && md5sum *.cfg *.conf | md5sum)"
OUT="$(inst "$CR" --clean-reinstall --dry-run)"
check "clean reinstall: --dry-run lists the files that would be put back, says which have your edits, and changes nothing" "echo \"\$OUT\" | grep -q 'would be put back' && echo \"\$OUT\" | grep -q 'Dry run: nothing was changed' && [ \"\$(cd $CRC && md5sum *.cfg *.conf | md5sum)\" = \"$CRALL0\" ]"
mkdir -p "$T/clrbefore"; for crf in printer.cfg saved_variables.cfg rpi_pi.cfg moonraker.conf KlipperScreen.conf ; do cp "$CRC/$crf" "$T/clrbefore/$crf"; done
OUT="$(inst "$CR" --clean-reinstall --yes)"
check "clean reinstall: a macro file with your own edit is back to this version, and the copy with your edit is saved in backup/ as name.wm-before-reset-<date>" "! grep -q MY_OWN_EDIT $CRC/macros.cfg && ls $CRC/backup/macros.cfg.wm-before-reset-* >/dev/null && grep -q MY_OWN_EDIT \$(ls $CRC/backup/macros.cfg.wm-before-reset-* | head -n1)"
check "clean reinstall: an rpi_*.cfg file with your own edit is back to the version of the repository" "cmp $ROOT/rpi-cfg/rpi_calibration.cfg $CRC/rpi_calibration.cfg && ls $CRC/backup/rpi_calibration.cfg.wm-before-reset-* >/dev/null"
check "clean reinstall: printer.cfg, saved_variables.cfg, moonraker.conf and KlipperScreen.conf keep your own lines (the normal update steps only add what is missing)" "for crf in printer.cfg saved_variables.cfg moonraker.conf KlipperScreen.conf; do grep -q machine.line $CRC/\$crf || exit 1; done; ! ls $CRC/backup/wm_my_overrides.cfg.wm-before-reset-* 2>/dev/null"
check "clean reinstall: it ends by saying how many files were put back, how many had your edits, and what was kept" "echo \"\$OUT\" | grep -q 'Clean reinstall: [0-9]* put back' && echo \"\$OUT\" | grep -q 'Not reset (your own lines stay): printer.cfg'"
OUT="$(inst "$CR" --clean-reinstall --yes)"
check "clean reinstall: a second run has nothing to put back" "echo \"\$OUT\" | grep -q 'Clean reinstall: 0 put back'"
check "clean reinstall: by hand the question defaults to no and nothing changes" "echo 'x' >> $CRC/change_macros.cfg; CRS1=\$(md5sum < $CRC/change_macros.cfg); echo | env \"WM_\"\"HOME=$CR\" WM_INSTALLER_TEST=1 bash $ROOT/installer.sh --clean-reinstall >/dev/null 2>&1; [ \"\$(md5sum < $CRC/change_macros.cfg)\" = \"\$CRS1\" ]"
check "clean reinstall: it is in the menu under Check and fix and in the header of installer.sh" "grep -q 'menu_item 7 \"Clean reinstall\"' $ROOT/installer.sh && grep -q 'menu_run --clean-reinstall' $ROOT/installer.sh && grep -q '^# ./installer.sh --clean-reinstall' $ROOT/installer.sh"
check "clean reinstall: wm_filemerge.py --reset puts the new version in place, saves your copy, records the baseline, and does nothing when the file is already the new version" "CRRS=\$(mktemp -d); { echo a; echo b; } > \$CRRS/new.cfg; { echo a; echo MINE; } > \$CRRS/live.cfg; mkdir \$CRRS/base; cp \$CRRS/new.cfg \$CRRS/base/new.cfg; python3 -I $ROOT/scripts/wm_filemerge.py \$CRRS/live.cfg \$CRRS/new.cfg \$CRRS/base --name new.cfg --write --stamp T --reset | grep -q 'had your edits'; cmp \$CRRS/live.cfg \$CRRS/new.cfg && grep -q MINE \$CRRS/backup/live.cfg.wm-before-reset-T && python3 -I $ROOT/scripts/wm_filemerge.py \$CRRS/live.cfg \$CRRS/new.cfg \$CRRS/base --name new.cfg --write --stamp T2 --reset | grep -q 'already the new version'"


sec "== 2.37.0: machine files (add a section, fix a line, remove an old line) and wm_my_overrides.cfg is gone"
MFH="$T/mfhome"; rm -rf "$MFH"; mkdir -p "$MFH/printer_data/config"; MFC="$MFH/printer_data/config"
printf '[mcu]\ncanbus_uuid: abc\n\n[printer]\nkind: corexy\nmax_velocity: 300\n\n[gcode_macro X]\ngcode:\n    M117 hi\n\n[include wm_my_overrides.cfg]\n\n#*# <---------------------- SAVE_CONFIG ---------------------->\n#*# DO NOT EDIT THIS BLOCK OR BELOW. The contents are auto-generated.\n#*#\n#*# [extruder]\n#*# control = pid\n' > "$MFC/printer.cfg"
printf '[server]\nhost: 0.0.0.0\n\n[authorization]\ncors_domains:\n  *.local\n' > "$MFC/moonraker.conf"
printf '[Variables]\nt0_offset = 1.5\n' > "$MFC/saved_variables.cfg"
printf '# comment only\n' > "$MFC/wm_my_overrides.cfg"
cat > "$T/mf.json" <<'MFJ'
{"entries":[
{"id":"a1","version":"9","file":"printer.cfg","op":"add_section","section":"gcode_macro NEW","lines":["gcode:","    M117 new"],"reason":"new macro"},
{"id":"a2","version":"9","file":"printer.cfg","op":"set_key","section":"printer","key":"max_velocity","value":"350","reason":"bug in the speed"},
{"id":"a3","version":"9","file":"moonraker.conf","op":"add_key","section":"server","key":"port","value":"7125","reason":"missing port"},
{"id":"a4","version":"9","file":"moonraker.conf","op":"remove_key","section":"authorization","key":"cors_domains","reason":"old line"},
{"id":"a5","version":"9","file":"saved_variables.cfg","op":"set_key","section":"Variables","key":"t0_offset","value":"9","reason":"must be refused"},
{"id":"a6","version":"9","file":"saved_variables.cfg","op":"add_key","section":"Variables","key":"newkey","value":"0","reason":"new key"},
{"id":"a7","version":"9","file":"wm_my_overrides.cfg","op":"add_key","section":"x","key":"y","value":"1","reason":"must be refused"},
{"id":"a8","version":"9","file":"printer.cfg","op":"set_key","section":"mcu","key":"canbus_uuid","value":"zzz","reason":"must be refused"}
]}
MFJ
echo "my own line" >> "$MFC/moonraker.conf"
MFS0="$(cd $MFC && md5sum printer.cfg moonraker.conf saved_variables.cfg wm_my_overrides.cfg | md5sum)"
WM_MACHINE_FIXES_LIST="$T/mf.json" inst "$MFH" --machine-files --dry-run > "$T/mf1.out"
check "machine files: --dry-run lists what would be added, fixed and removed and changes nothing" "grep -q 'added section \[gcode_macro NEW\]' $T/mf1.out && grep -q 'fixed \[printer\] max_velocity: 300 -> 350' $T/mf1.out && grep -q 'removed \[authorization\] cors_domains' $T/mf1.out && [ \"\$(cd $MFC && md5sum printer.cfg moonraker.conf saved_variables.cfg wm_my_overrides.cfg | md5sum)\" = \"$MFS0\" ]"
SAVEBLK0="$(sed -n '/SAVE_CONFIG/,$p' $MFC/printer.cfg | md5sum)"
WM_MACHINE_FIXES_LIST="$T/mf.json" inst "$MFH" --machine-files --yes > "$T/mf2.out"
check "machine files: a new section lands above the SAVE_CONFIG block and the block itself is byte for byte the same" "awk '/gcode_macro NEW/{a=NR} /SAVE_CONFIG/{s=NR} END{exit !(a>0 && a<s)}' $MFC/printer.cfg && [ \"\$(sed -n '/SAVE_CONFIG/,\$p' $MFC/printer.cfg | md5sum)\" = \"$SAVEBLK0\" ]"
check "machine files: a line with a bug is fixed even when it is the user's value, and the report names the old and new value and the reason" "grep -q 'max_velocity: 350' $MFC/printer.cfg && grep -q '300 -> 350.*bug in the speed' $T/mf2.out"
check "machine files: a missing key is added, an old key is removed, and the other lines of the user stay" "grep -q '^port: 7125' $MFC/moonraker.conf && ! grep -q cors_domains $MFC/moonraker.conf && grep -q 'my own line' $MFC/moonraker.conf && grep -q 'host: 0.0.0.0' $MFC/moonraker.conf"
check "machine files: every changed file has a copy in backup/ first" "ls $MFC/backup/printer.cfg.wm-before-machine-fixes-* >/dev/null && ls $MFC/backup/moonraker.conf.wm-before-machine-fixes-* >/dev/null && grep -q 'max_velocity: 300' \$(ls $MFC/backup/printer.cfg.wm-before-machine-fixes-* | head -n1)"
check "machine files: calibration values in saved_variables.cfg are never changed (only a new key is added)" "grep -q 't0_offset = 1.5' $MFC/saved_variables.cfg && grep -q 'newkey = 0' $MFC/saved_variables.cfg && grep -q 'calibration values are never changed' $T/mf2.out"
check "machine files: the CAN id is refused" "grep -q 'canbus_uuid: abc' $MFC/printer.cfg && grep -q 'refused  printer.cfg: a8' $T/mf2.out"
MFU="$T/mfuser"; rm -rf "$MFU"; mkdir -p "$MFU"; printf '[Variables]\nx = 1\n' > "$MFU/saved_variables.cfg"; printf '# mine\n[gcode_macro MINE]\nvariable_a: 1\n' > "$MFU/wm_my_overrides.cfg"; printf '[printer]\nkind: x\n' > "$MFU/printer.cfg"
MFU1="$(md5sum $MFU/wm_my_overrides.cfg | cut -c1-32)"
python3 -I $ROOT/scripts/wm_machine_fixes.py "$MFU" --list "$T/mf.json" --write --stamp U1 > "$T/mfu.out"
check "machine files: a file of the user (wm_my_overrides.cfg) is refused and never changed" "grep -q 'refused  wm_my_overrides.cfg: a7' $T/mfu.out && [ \"\$(md5sum $MFU/wm_my_overrides.cfg | cut -c1-32)\" = \"$MFU1\" ]"
sed -i 's/^max_velocity: 350/max_velocity: 280/' "$MFC/printer.cfg"
WM_MACHINE_FIXES_LIST="$T/mf.json" inst "$MFH" --machine-files --yes > "$T/mf3.out"
check "machine files: a second run does nothing, a fix is applied only once (a later change of the user stays)" "grep -q 'max_velocity: 280' $MFC/printer.cfg && ! grep -q 'bug in the speed' $T/mf3.out"
: > "$MFC/saved_variables.cfg"
WM_MACHINE_FIXES_LIST="$T/mf.json" inst "$MFH" --machine-files --yes > "$T/mf4.out"
check "machine files: an empty saved_variables.cfg is reported and, with --yes and nobody to answer, it is NOT replaced" "grep -q 'saved_variables.cfg is missing or damaged' $T/mf4.out && [ ! -s $MFC/saved_variables.cfg ]"
printf '[Variables]\nt0_offset = 2.5\n' > "$MFC/saved_variables.cfg.wm-good"
echo y | env "WM_""HOME=$MFH" WM_INSTALLER_TEST=1 WM_MACHINE_FIXES_LIST="$T/mf.json" bash $ROOT/installer.sh --machine-files > "$T/mf5.out" 2>&1
check "machine files: asked by hand and answered yes, the damaged saved_variables.cfg is replaced with the last good copy and the damaged one is kept in backup/" "grep -q 't0_offset = 2.5' $MFC/saved_variables.cfg && ls $MFC/backup/saved_variables.cfg.wm-before-replace-* >/dev/null"
check "wm_my_overrides.cfg: an update removes an empty file (only comments) and its include line, with copies in backup/" "[ ! -e $MFC/wm_my_overrides.cfg ] && ! grep -q wm_my_overrides $MFC/printer.cfg && ls $MFC/backup/wm_my_overrides.cfg.wm-before-removal-* >/dev/null && ls $MFC/backup/printer.cfg.wm-before-overrides-removal-* >/dev/null"
printf '# header\n[gcode_macro MINE]\nvariable_a: 1\n' > "$MFC/wm_my_overrides.cfg"; printf '\n[include wm_my_overrides.cfg]\n' >> "$MFC/printer.cfg.tmp"; sed -i 's/^\[gcode_macro X\]/[include wm_my_overrides.cfg]\n[gcode_macro X]/' "$MFC/printer.cfg"; rm -f "$MFC/printer.cfg.tmp"
MFS1="$(cd $MFC && md5sum printer.cfg wm_my_overrides.cfg | md5sum)"
inst "$MFH" --machine-files --yes > "$T/mf6.out"
check "wm_my_overrides.cfg: a file with the user's own lines stays, with its include line, and the update says it is the user's own file now" "[ \"\$(cd $MFC && md5sum printer.cfg wm_my_overrides.cfg | md5sum)\" = \"$MFS1\" ] && grep -q 'your own file now' $T/mf6.out"
check "wm_my_overrides.cfg: the installer no longer creates it or has the --my-overrides command" "! grep -q -- '--my-overrides' $ROOT/installer.sh && ! grep -q 'Created wm_my_overrides' $ROOT/installer.sh"
check "machine files: the shipped list is valid and --machine-files is in the header of installer.sh" "python3 -c \"import json;json.load(open('$ROOT/scripts/wm_machine_fixes.json'))\" && grep -q '^# ./installer.sh --machine-files' $ROOT/installer.sh"

repo_guard

if [ "$(real_sum)" = "$REAL_SUM0" ]; then PASS=$((PASS+1)); echo "  ok   the real home of this machine was not touched (Klipper's driver links, config file list, moonraker.conf)"
else FAIL=$((FAIL+1)); echo "  FAIL the real home of this machine changed during the run (Klipper's driver links, config file list or moonraker.conf): a test did not use its fake home, or the printer was used during the run"; find "$REAL_HOME/klipper/klippy/extras" -maxdepth 1 -type l -printf '        | %f -> %l\n' 2>/dev/null; fi

echo; echo "slowest sections:"; sort -rn "$T/.sectimes" | head -n 12 | sed "s/^/  /"
echo; echo "passed: $PASS  failed: $FAIL"; [ "$FAIL" = 0 ]
