/*global ut */
var term, eng; // Can't be initialized yet because DOM is not ready
var xsize = 61;
var ysize = 61;
var pl = { x: 2*xsize, y: ysize-1 }; // Player position
var updateFOV; // For some of the examples
var xomap = [
".....................................",
".#######......#######.###########....",   
"..#:::::#....#:::::###:::::::::::##..", 
"...#:::::#..#:::::##:::::::::::::::#.",
"....#:::::##:::::# #:::::#####:::::#.",
".....#::::::::::#  #::::#     #::::#.",
"......#::::::::#   #::::#     #::::#.",
"......#::::::::#   #::::#     #::::#.",
".....#::::::::::#  #::::#     #::::#.",
"....#:::::##:::::# #:::::#####:::::#.",
"...#:::::#..#:::::##:::::::::::::::#.",
"..#:::::#....#:::::###:::::::::::##..", 
".#######......#######.###########....",
".....................................",
];


// The tile palette is precomputed in order to not have to create
// thousands of Tiles on the fly.
var AT = new ut.Tile("@", 255, 255, 255);
var WALL = new ut.Tile('▒', 100, 100, 100);
var FLOOR = new ut.Tile('.', 50, 50, 50);

// Returns a Tile based on the char array map
function getDungeonTile(x, y) {
	var t = "";
	try { t = map[y][x]; }
	catch(err) { return ut.NULLTILE; }
	if (t === '#') return WALL;
	if (t === '.') return FLOOR;
	return ut.NULLTILE;
}

// "Main loop"
function tick() {
	if (updateFOV) updateFOV(pl.x, pl.y); // Update field of view (used in some examples)
	eng.update(pl.x, pl.y); // Update tiles
	term.put(AT, term.cx, term.cy); // Player character
	term.render(); // Render
}

// Key press handler - movement & collision handling
function onKeyDown(k) {
	var movedir = { x: 0, y: 0 }; // Movement vector
	if (k === ut.KEY_LEFT || k === ut.KEY_H) movedir.x = -1;
	else if (k === ut.KEY_RIGHT || k === ut.KEY_L) movedir.x = 1;
	else if (k === ut.KEY_UP || k === ut.KEY_K) movedir.y = -1;
	else if (k === ut.KEY_DOWN || k === ut.KEY_J) movedir.y = 1;
	if (movedir.x === 0 && movedir.y === 0) return;
	var oldx = pl.x, oldy = pl.y;
	pl.x += movedir.x;
	pl.y += movedir.y;
	if (eng.tileFunc(pl.x, pl.y).getChar() !== '.') { pl.x = oldx; pl.y = oldy; }
	tick();
}

// Maze functions modified from the ones at 
// http://rosettacode.org/wiki/Maze_generation#JavaScript
function mazegen(x,y) {
    var n=x*y-1;
    if (n<0) {alert("illegal maze dimensions");return;}
    var horiz=[]; for (var j= 0; j<x+1; j++) horiz[j]= [];
    var verti=[]; for (var j= 0; j<y+1; j++) verti[j]= [];
    var here= [Math.floor(Math.random()*x), Math.floor(Math.random()*y)];
    var path= [here];
    var unvisited= [];
    for (var j= 0; j<x+2; j++) {
        unvisited[j]= [];
        for (var k= 0; k<y+1; k++)
            unvisited[j].push(j>0 && j<x+1 && k>0 && (j != here[0]+1 || k != here[1]+1));
    }
    var fmxlen= xomap[0].length;
    var fmylen= xomap.length;
    var fmxlbound= Math.floor((x - fmxlen) / 2);
    var fmxubound= fmxlbound + fmxlen;
    var fmylbound= Math.floor((y - fmylen) / 2);
    var fmyubound= fmylbound + fmylen;
    while (0<n) {
        var potential= [[here[0]+1, here[1]], [here[0],here[1]+1],
            [here[0]-1, here[1]], [here[0],here[1]-1]];
        var neighbors= [];
        for (var j= 0; j < 4; j++)
            if (unvisited[potential[j][0]+1][potential[j][1]+1])
                neighbors.push(potential[j]);
        if (neighbors.length) {
            n= n-1;
            next= neighbors[Math.floor(Math.random()*neighbors.length)];
            unvisited[next[0]+1][next[1]+1]= false;
            if (next[0] == here[0])
                horiz[next[0]][(next[1]+here[1]-1)/2]= true;
            else 
                verti[(next[0]+here[0]-1)/2][next[1]]= true;
            path.push(here= next);
        } else 
            here= path.pop();
    }
    return ({x: x, y: y, horiz: horiz, verti: verti});
}
 
function mazedisplay(m) {
    var fmxlen= xomap[0].length;
    var fmylen= xomap.length;
    var fmxlbound= Math.floor(2*m.x - fmxlen/2);
    var fmxubound= fmxlbound + fmxlen;
    var fmylbound= Math.floor(m.y - fmylen/2);
    var fmyubound= fmylbound + fmylen;
    var text= [];
    for (var j= 0; j<m.x*2+1; j++) {
        var line= [];
        if (0 == j%2)
            for (var k=0; k<m.y*4+1; k++)
                if (0 == k%4) 
                    line[k]= '#';
                else
                    if (j>0 && m.verti[j/2-1][Math.floor(k/4)])
                        line[k]= '.';
                    else
                        line[k]= '#';
        else
            for (var k=0; k<m.y*4+1; k++)
                if (0 == k%4)
                    if (k>0 && m.horiz[(j-1)/2][k/4-1])
                        line[k]= '.';
                    else
                        line[k]= '#';
                else
                    line[k]= '.';
        if (0 == j) line[1]= line[2]= line[3]= '.';
        if (m.x*2-1 == j) line[4*m.y]= '.';
        var l = line.join('');
        if (fmylbound <= j && j < fmyubound){
            var ll = l.slice(0, fmxlbound);
            var lu = l.slice(fmxubound, 4*m.x+1);
            l = ll + xomap[j-fmylbound] + lu;
        }
        text.push(l);
    }
    return text;
}

var map = mazedisplay(mazegen(xsize, ysize))

// Initialize stuff
function initXoDungeon() {
	window.setInterval(tick, 50); // Animation
	// Initialize Viewport, i.e. the place where the characters are displayed
	term = new ut.Viewport(document.getElementById("game"), 61, 15);
	// Initialize Engine, i.e. the Tile manager
	eng = new ut.Engine(term, getDungeonTile, map[0].length, map.length);
	// Initialize input
	ut.initInput(onKeyDown);
}




