import sys
out=sys.argv[1]
F='font-family="Roboto,DejaVu Sans,Arial,sans-serif"'
def nozzle(cx, tipbot, s=1.0):
    tw=14*s; th=22*s; cw=52*s; ch=46*s; bw=74*s; bh=40*s
    t=tipbot-th; c=t-ch; b=c-bh
    return (f'<rect x="{cx-bw/2:.1f}" y="{b:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="5" fill="#3a3f47" stroke="#8a919c" stroke-width="1.5"/>'
            f'<polygon points="{cx-cw/2:.1f},{c:.1f} {cx+cw/2:.1f},{c:.1f} {cx+tw/2:.1f},{t:.1f} {cx-tw/2:.1f},{t:.1f}" fill="#b8923f" stroke="#e6c779" stroke-width="1.5"/>'
            f'<rect x="{cx-tw/2:.1f}" y="{t:.1f}" width="{tw:.1f}" height="{th:.1f}" fill="#d9b25a" stroke="#f1d894" stroke-width="1.5"/>'
            f'<line x1="{cx-tw/2-5:.1f}" y1="{t+th/2:.1f}" x2="{cx+tw/2+5:.1f}" y2="{t+th/2:.1f}" stroke="#ff5252" stroke-width="4"/>')
BL='fill="#e8eaed" stroke="#ffffff" stroke-width="1.5"'
def front(cx, top, s, dz, bw, bh, gap, pw):
    return (f'<rect x="{cx-bw/2}" y="{top}" width="{bw}" height="{bh}" rx="3" {BL}/>'
            f'<rect x="{cx+bw/2+gap}" y="{top}" width="{pw}" height="{bh}" rx="2" {BL}/>' + nozzle(cx, top+dz, s))
W,H=300,400
def svg(body): return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" {F}><rect width="{W}" height="{H}" rx="8" fill="#1e1e22"/>{body}</svg>'
def title(t): return f'<text x="14" y="30" fill="#ffffff" font-size="19" font-weight="700">{t}</text>'
# 1 height
top=250; s=1.5; cx=178
b=title("1. Height, from the front")
b+=front(cx, top, s, 11*s, 104, 136, 10, 26)
b+=f'<line x1="8" y1="{top}" x2="292" y2="{top}" stroke="#4fc3f7" stroke-width="2.5" stroke-dasharray="8 5"/>'
b+=f'<text x="10" y="{top-10}" fill="#4fc3f7" font-size="17" font-weight="700">block top</text>'
b+=f'<text x="10" y="{top+62}" fill="#ff8a80" font-size="17" font-weight="700">middle</text><text x="10" y="{top+83}" fill="#ff8a80" font-size="17" font-weight="700">of the tip</text>'
b+=f'<line x1="72" y1="{top+44}" x2="{cx-18}" y2="{top+5}" stroke="#ff8a80" stroke-width="2"/>'
b+=f'<text x="{cx}" y="{top+122}" fill="#30343a" font-size="14" font-weight="700" text-anchor="middle">metal block</text>'
b+=f'<text x="{cx}" y="62" fill="#cfd3d8" font-size="16" text-anchor="middle">T0 nozzle</text>'
open(out+"/setter-height.svg","w").write(svg(b))
# 2 place
k=14.0; nx=118; ny=236; by=ny-5.8*k; px=nx+6.9*k; L=8.6*k; T=2.6*k
b=title("2. Place, from above")
b+=f'<rect x="{nx-L/2:.1f}" y="{by-T/2:.1f}" width="{L:.1f}" height="{T:.1f}" rx="3" {BL}/><rect x="{px-T/2:.1f}" y="{ny-L/2:.1f}" width="{T:.1f}" height="{L:.1f}" rx="3" {BL}/>'
b+=f'<line x1="{nx}" y1="{by-T/2-8:.1f}" x2="{nx}" y2="{ny+30}" stroke="#69f0ae" stroke-width="1.5" stroke-dasharray="4 4"/><line x1="{nx-50}" y1="{ny}" x2="{px+T/2+8:.1f}" y2="{ny}" stroke="#69f0ae" stroke-width="1.5" stroke-dasharray="4 4"/>'
b+=f'<circle cx="{nx}" cy="{ny}" r="{2.0*k:.1f}" fill="none" stroke="#e6c779" stroke-width="1.5" stroke-dasharray="4 4"/><circle cx="{nx}" cy="{ny}" r="{0.8*k:.1f}" fill="#d9b25a" stroke="#f1d894" stroke-width="1.5"/>'
b+='<defs><marker id="a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#69f0ae"/></marker></defs>'
b+=f'<line x1="{nx}" y1="{ny-15}" x2="{nx}" y2="{by+T/2+5:.1f}" stroke="#69f0ae" stroke-width="3" marker-end="url(#a)"/><line x1="{nx+15}" y1="{ny}" x2="{px-T/2-5:.1f}" y2="{ny}" stroke="#69f0ae" stroke-width="3" marker-end="url(#a)"/>'
b+=f'<text x="{nx-12}" y="{(ny+by)/2+2:.1f}" fill="#69f0ae" font-size="17" font-weight="700" text-anchor="end">6 mm</text>'
b+=f'<text x="{nx+44}" y="{ny-12}" fill="#69f0ae" font-size="17" font-weight="700" text-anchor="middle">7 mm</text>'
b+=f'<text x="{nx}" y="{by-T/2-14:.1f}" fill="#cfd3d8" font-size="16" text-anchor="middle">metal block</text>'
b+=f'<text x="{px+T/2+4:.1f}" y="{ny+L/2+22:.1f}" fill="#cfd3d8" font-size="16" text-anchor="end">metal block</text>'
b+=f'<text x="{nx-6}" y="{ny+2.0*k+24:.1f}" fill="#cfd3d8" font-size="16" text-anchor="middle">T0 nozzle</text>'
b+=f'<text x="150" y="{H-36}" fill="#ffffff" font-size="16" text-anchor="middle">Nozzle in line with the</text><text x="150" y="{H-15}" fill="#ffffff" font-size="16" text-anchor="middle">middle of both blocks</text>'
open(out+"/setter-place.svg","w").write(svg(b))
# 3 compare
b=title("3. Red line and blue line")
for i,(t,a,col,dz) in enumerate([("LOW","Z plus","#ff8a80",30),("RIGHT","Save","#69f0ae",8.5),("HIGH","Z minus","#ffd180",-16)]):
    x0=8+i*96; tp=240
    b+=f'<rect x="{x0}" y="46" width="92" height="344" rx="6" fill="#26272c" stroke="{col}" stroke-width="{3 if t=="RIGHT" else 1.5}"/>'
    b+=f'<text x="{x0+46}" y="74" fill="{col}" font-size="18" font-weight="700" text-anchor="middle">{t}</text>'
    b+=front(x0+38, tp, 0.78, dz, 52, 84, 6, 13)
    b+=f'<line x1="{x0+5}" y1="{tp}" x2="{x0+87}" y2="{tp}" stroke="#4fc3f7" stroke-width="2" stroke-dasharray="6 4"/>'
    b+=f'<text x="{x0+46}" y="356" fill="#ffffff" font-size="16" text-anchor="middle">press</text><text x="{x0+46}" y="378" fill="#ffffff" font-size="17" font-weight="700" text-anchor="middle">{a}</text>'
open(out+"/setter-compare.svg","w").write(svg(b))
