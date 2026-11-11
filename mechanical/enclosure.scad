// Mesa Voice rev A - mechanical source, millimetres.
// Own geometry CC-BY-4.0. See ../docs/mechanical.md for tolerances/assembly.
// X/Y are the carrier PCB axes; +Z points upwards in assembled coordinates.
// Exportable parts are already oriented for FDM printing, flat on Z=0.
part = "assembly"; // base, lid, speaker_clamp, assembly, exploded, footprint
$fn = 64;

case_x=94; case_y=82; base_h=40; lid_t=2;
wall=2; floor_t=2; corner_r=5;
pcb_origin=[7,9]; pcb_size=[64,54]; pcb_z=6; pcb_t=1.6;
pcb_holes=[[3,3],[61,3],[3,51],[61,51]];
case_screws=[[5,5],[89,5],[5,77],[89,77]];
speaker=[60,47]; speaker_rim_d=40.0; speaker_pocket_d=40.6;
speaker_clamp_inner_d=36.8; speaker_clamp_outer_d=44.6;
speaker_screw_radius=25.5; speaker_seat_z=2.7; clamp_z=4.0;
button=[76,16]; button_hole_d=16.1;
button_nut_d=22; // reserve nut, washer and tightening clearance, not only M16 body
led=[87,29]; led_hole_d=3.2;
mic=[22,18];
usb_x=22; usb_z=19; usb_w=18; usb_h=14;
// z for lid() is distance from its exterior face towards its interior.
function lid_xy(p)=[p[0],case_y-p[1]];

assert(wall>=2 && floor_t>=2,"Minimum FDM walls: 2 mm");
assert(pcb_z+pcb_t+25 < base_h-2.5,"Module envelope touches lid lip");
assert(case_y-wall-1.8-(pcb_origin[1]+pcb_size[1])>=15,"Antenna to PCB edge <15mm");
assert(speaker_pocket_d>speaker_rim_d+0.4,"Insufficient speaker clearance");

module rr2d(w,d,r) {
    translate([r,r]) offset(r=r) square([w-2*r,d-2*r]);
}
module rr(w,d,h,r) { linear_extrude(height=h) rr2d(w,d,r); }
module hole(p,d,h,z=-0.1) { translate([p[0],p[1],z]) cylinder(d=d,h=h); }

module base() {
    difference() {
        union() {
            difference() {
                rr(case_x,case_y,base_h,corner_r);
                translate([wall,wall,floor_t])
                    rr(case_x-2*wall,case_y-2*wall,base_h,corner_r-wall);
            }
            // PCB bosses. M3x5 screws, 2.5mm pilots, no metal inserts needed.
            for(p=pcb_holes)
                translate([pcb_origin[0]+p[0],pcb_origin[1]+p[1],floor_t-0.1])
                    cylinder(d=6.8,h=pcb_z-floor_t+0.1);
            // Four lid bosses with short ribs to their adjacent enclosure walls.
            for(p=case_screws) {
                translate([p[0],p[1],floor_t-0.1]) cylinder(d=8,h=base_h-floor_t+0.1);
                translate([p[0]<case_x/2 ? 1 : case_x-5,p[1]-1.2,floor_t])
                    cube([4,2.4,base_h-floor_t]);
            }
            // Two wire-tie bridges, kept away from the PCB/antenna envelope.
            for(p=[[21,70],[45,70]]) translate([p[0]-4,p[1]-2,floor_t-0.1])
                difference() { cube([8,4,4.1]); translate([2,-0.1,0]) cube([4,4.2,2.2]); }
        }
        for(p=pcb_holes)
            hole([pcb_origin[0]+p[0],pcb_origin[1]+p[1]],2.5,pcb_z-floor_t+0.6,floor_t-0.5);
        for(p=case_screws) hole(p,2.5,10.2,base_h-10);
        // Oversized port includes plug overmould access, not just connector shell.
        translate([usb_x-usb_w/2,-0.1,usb_z-usb_h/2]) cube([usb_w,wall+0.2,usb_h]);
        // Left cooling slots leave the rear antenna adhesive area uninterrupted.
        // They do not provide an IP seal.
        for(y=[34:8:58]) translate([-0.1,y,10]) cube([wall+0.2,3,8]);
    }
}

module grille_holes(center,radius,pitch=3.8,d=2.4) {
    for(x=[-radius:pitch:radius],y=[-radius:pitch:radius])
        if(x*x+y*y < (radius-d/2)*(radius-d/2))
            hole([center[0]+x,center[1]+y],d,lid_t+0.3);
}
module lid() {
    s=lid_xy(speaker); b=lid_xy(button); l=lid_xy(led); m=lid_xy(mic);
    difference() {
        union() {
            rr(case_x,case_y,lid_t,corner_r);
            // Loose locating lip; interrupted around screw bosses.
            difference() {
                translate([2.3,2.3,lid_t-0.1]) rr(case_x-4.6,case_y-4.6,2.6,2.7);
                translate([3.7,3.7,lid_t-0.2]) rr(case_x-7.4,case_y-7.4,2.9,1.3);
                for(p=case_screws) hole(lid_xy(p),9.1,3.0,lid_t-0.2);
            }
            // Side pocket locates only the metal flange; grille is the front seat.
            translate([s[0],s[1],lid_t-0.1]) difference() {
                cylinder(d=speaker_clamp_outer_d,h=2.1);
                translate([0,0,-0.1]) cylinder(d=speaker_pocket_d,h=2.3);
            }
            for(a=[0,90,180,270])
                translate([s[0]+speaker_screw_radius*cos(a),s[1]+speaker_screw_radius*sin(a),lid_t-0.1])
                    cylinder(d=5.8,h=clamp_z-lid_t+0.1);
            // Reinforce the panel around the 4 N pushbutton. 3.5 mm total panel.
            hole(b,button_nut_d,1.6,lid_t-0.1);
        }
        for(p=case_screws) hole(lid_xy(p),3.2,lid_t+0.3);
        grille_holes(s,18.0);
        // Broad mic grille tolerates the expansion-board revision/stack position.
        for(x=[-7.5:3:7.5],y=[-9:3:9]) hole([m[0]+x,m[1]+y],1.5,lid_t+0.3);
        hole(b,button_hole_d,lid_t+1.8);
        hole(l,led_hole_d,lid_t+0.3);
        for(a=[0,90,180,270])
            hole([s[0]+speaker_screw_radius*cos(a),s[1]+speaker_screw_radius*sin(a)],1.65,clamp_z-0.9,1.0);
    }
}

module speaker_clamp() {
    // Print flat. Assembly bottom sits at lid z=4, above compressed gasket/rim.
    difference() {
        union() {
            cylinder(d=speaker_clamp_outer_d,h=2);
            for(a=[0,90,180,270]) hull() {
                rotate([0,0,a]) translate([20,0,0]) cylinder(d=5.8,h=2);
                rotate([0,0,a]) translate([speaker_screw_radius,0,0]) cylinder(d=5.8,h=2);
            }
        }
        translate([0,0,-0.1]) cylinder(d=speaker_clamp_inner_d,h=2.2);
        for(a=[0,90,180,270]) rotate([0,0,a])
            translate([speaker_screw_radius,0,-0.1]) cylinder(d=2.2,h=2.2);
        // Two solder-terminal/wire slots; rotate speaker to align with them.
        for(a=[45,225]) rotate([0,0,a]) translate([17,-2.5,-0.1]) cube([7,5,1.2]);
    }
}

module envelopes() {
    // Conservative bounding geometry only: not manufacturer STEP models.
    color([0,0.45,0.25,0.8]) translate([pcb_origin[0],pcb_origin[1],pcb_z]) cube([64,54,pcb_t]);
    color([0.25,0.25,0.25,0.7]) translate([pcb_origin[0]+6.1,pcb_origin[1]-1.5,pcb_z+pcb_t]) cube([17.8,21,25]);
    color([0.1,0.4,0.7,0.7]) translate([pcb_origin[0]+33.3,pcb_origin[1]+19.46,pcb_z+pcb_t]) cube([19.4,17.84,22]);
    color([0.7,0.7,0.7,0.7]) translate([button[0],button[1],base_h+lid_t-18.5]) cylinder(d=16,h=18.5);
    color([0.5,0.5,0.5,0.7]) translate([button[0],button[1],36]) cylinder(d=button_nut_d,h=2.5);
    color([0.1,0.1,0.1,0.7]) translate([speaker[0],speaker[1],base_h+lid_t-speaker_seat_z]) {
        translate([0,0,-1.3]) cylinder(d=40.2,h=1.3);
        translate([0,0,-4.6]) cylinder(d=36.3,h=3.3);
    }
    color([0.1,0.1,0.1,0.6]) translate([10,case_y-wall-1.8,16]) cube([37.4,1.8,17.5]);
}
// Independent fit export: collisions of nominal component envelopes with printed
// parts. Small inset avoids treating intended mating-plane contact as penetration.
// No claim about cable flexibility, acoustic seal, tolerances or connector detail.
module printed_assembly() {
    base();
    translate([0,case_y,base_h+lid_t]) rotate([180,0,0]) {
        lid();
        translate([speaker[0],case_y-speaker[1],clamp_z]) speaker_clamp();
    }
}
module component_keepouts() {
    translate([pcb_origin[0]+0.02,pcb_origin[1]+0.02,pcb_z+0.02]) cube([63.96,53.96,pcb_t-0.04]);
    translate([13.1,7.5,7.62]) cube([17.8,21,24.96]); // Sense incl. headers
    translate([40.3,28.46,7.62]) cube([19.4,17.84,21.96]); // amp incl. terminal
    for(p=[[16,49],[27,53]]) translate([p[0]-2.5,p[1]-3,7.62]) cube([7.5,6,11.98]); // JST mates
    translate([button[0],button[1],23.5]) cylinder(d=15.96,h=18.48);
    translate([button[0],button[1],36.02]) cylinder(d=button_nut_d-0.04,h=2.46);
    translate([led[0],led[1],32]) cylinder(d=2.96,h=9.98);
    translate([led[0],led[1],38]) cylinder(d=3.8,h=1.98);
    translate([speaker[0],speaker[1],38.02]) cylinder(d=40.2,h=1.26);
    translate([speaker[0],speaker[1],34.7]) cylinder(d=36.3,h=3.28);
    translate([10,78.22,16]) cube([37.4,1.76,17.5]);
}
module fitcheck() {
    intersection() { printed_assembly(); component_keepouts(); }
    // USB overmould path (16 x 12 mm); excluded from module-vs-module checks.
    intersection() { base(); translate([14,-1,13]) cube([16,13,12]); }
    // PCB screw heads vs modules, and button nut vs speaker envelope.
    intersection() {
        union() for(p=pcb_holes) translate([pcb_origin[0]+p[0],pcb_origin[1]+p[1],7.62]) cylinder(d=5.5,h=3);
        union() {
            translate([13.1,7.5,7.62]) cube([17.8,21,24.96]);
            translate([40.3,28.46,7.62]) cube([19.4,17.84,21.96]);
        }
    }
}
module assembly(explode=0) {
    color([0.75,0.77,0.79,1]) base();
    envelopes();
    translate([0,case_y,base_h+lid_t+explode]) rotate([180,0,0]) {
        color([0.9,0.91,0.92,1]) lid();
        translate([speaker[0],case_y-speaker[1],clamp_z]) color([0.4,0.45,0.5,1]) speaker_clamp();
    }
}

if(part=="base") base();
else if(part=="lid") lid();
else if(part=="speaker_clamp") speaker_clamp();
else if(part=="assembly") assembly();
else if(part=="exploded") assembly(28);
else if(part=="footprint") projection(cut=false) lid();
else if(part=="fitcheck") fitcheck();
else assert(false,"Unknown part");
