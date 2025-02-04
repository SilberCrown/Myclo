// static/tetris.js

const canvas = document.getElementById("tetris-canvas");
const ctx = canvas.getContext("2d");
const scoreElement = document.getElementById("score");
const COLS = 10;
const ROWS = 20;
const BLOCK_SIZE = 20;

let score = 0;
let grid = createMatrix(COLS, ROWS);  // 2次元配列 [y][x]
let currentPiece;
let dropCounter = 0;
let dropInterval = 1000; // ミリ秒
let lastTime = 0;

initGame();
update(0);

// キー操作
document.addEventListener("keydown", event => {
  if (!currentPiece) return;
  switch(event.key) {
    case "ArrowLeft":
      move(-1);
      break;
    case "ArrowRight":
      move(1);
      break;
    case "ArrowDown":
      drop();
      break;
    case "ArrowUp":
      rotate();
      break;
    case "Escape":
      resetGame();
      break;
    case " ":
      hardDrop();
      break;
  }
});

function initGame() {
  resetPiece();
  draw();
}

function resetGame() {
  score = 0;
  grid = createMatrix(COLS, ROWS);
  resetPiece();
  draw();
}

function goHome() {
  window.location.href = "/";
}

function update(time = 0) {
  const deltaTime = time - lastTime;
  lastTime = time;
  dropCounter += deltaTime;
  if (dropCounter > dropInterval) {
    drop();
  }
  draw();
  requestAnimationFrame(update);
}

function createMatrix(w, h) {
  const matrix = [];
  for (let i = 0; i < h; i++){
    matrix.push(new Array(w).fill(0));
  }
  return matrix;
}

// テトリミノの形
const PIECES = [
  [[1,1,1,1]],          // I
  [[2,2],[2,2]],        // O
  [[0,3,0],[3,3,3]],    // T
  [[0,4,4],[4,4,0]],    // S
  [[5,5,0],[0,5,5]],    // Z
  [[6,6,6],[6,0,0]],    // J
  [[7,7,7],[0,0,7]],    // L
];

function resetPiece() {
  const rand = (Math.random()*PIECES.length)|0;
  const shape = PIECES[rand];
  currentPiece = {
    matrix: shape.map(row => row.slice()), // clone
    x: (COLS / 2 | 0) - (shape[0].length / 2 | 0),
    y: 0
  };
  if (collide(grid, currentPiece)) {
    // Game Over
    grid.forEach(row => row.fill(0));
    score = 0;
  }
  dropCounter = 0;
}

function drop() {
  currentPiece.y++;
  if (collide(grid, currentPiece)) {
    currentPiece.y--;
    merge(grid, currentPiece);
    resetPiece();
    clearLines();
  }
  dropCounter = 0;
}

function hardDrop() {
  while(!collide(grid, currentPiece)){
    currentPiece.y++;
  }
  currentPiece.y--;
  merge(grid, currentPiece);
  resetPiece();
  clearLines();
  dropCounter = 0;
}

function move(dir) {
  currentPiece.x += dir;
  if (collide(grid, currentPiece)) {
    currentPiece.x -= dir;
  }
}

function rotate() {
  const m = currentPiece.matrix;
  // transpose + reverse row = rotate 90
  for (let y = 0; y < m.length; y++){
    for (let x = 0; x < y; x++){
      [m[x][y], m[y][x]] = [m[y][x], m[x][y]];
    }
  }
  m.forEach(row => row.reverse());
  // check collision
  if (collide(grid, currentPiece)) {
    // revert
    m.forEach(row => row.reverse());
    for (let y = 0; y < m.length; y++){
      for (let x = 0; x < y; x++){
        [m[x][y], m[y][x]] = [m[y][x], m[x][y]];
      }
    }
  }
}

function collide(matrix, piece) {
  for (let y = 0; y < piece.matrix.length; y++){
    for (let x = 0; x < piece.matrix[y].length; x++){
      if (piece.matrix[y][x] !== 0) {
        let nx = piece.x + x;
        let ny = piece.y + y;
        if (nx < 0 || nx >= COLS || ny >= ROWS || (ny >= 0 && matrix[ny][nx] !== 0)) {
          return true;
        }
      }
    }
  }
  return false;
}

function merge(matrix, piece) {
  for (let y=0; y < piece.matrix.length; y++){
    for (let x=0; x < piece.matrix[y].length; x++){
      if (piece.matrix[y][x] !== 0) {
        matrix[piece.y + y][piece.x + x] = piece.matrix[y][x];
      }
    }
  }
}

function clearLines() {
  let linesCleared = 0;
  for (let y=0; y<ROWS; y++){
    if (grid[y].every(val => val !== 0)) {
      grid.splice(y,1);
      grid.unshift(new Array(COLS).fill(0));
      linesCleared++;
    }
  }
  score += linesCleared * 10;
}

function draw() {
  ctx.clearRect(0,0,canvas.width, canvas.height);

  // draw placed blocks
  drawMatrix(grid, {x:0, y:0});
  // draw current piece
  if (currentPiece) {
    drawMatrix(currentPiece.matrix, {x: currentPiece.x, y: currentPiece.y});
  }
  scoreElement.textContent = "SCORE: " + score;
}

function drawMatrix(matrix, offset) {
  for (let y=0; y<matrix.length; y++){
    for (let x=0; x<matrix[y].length; x++){
      const val = matrix[y][x];
      if (val !== 0) {
        ctx.fillStyle = getColor(val);
        ctx.fillRect((x+offset.x)*BLOCK_SIZE, (y+offset.y)*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
        ctx.strokeStyle = "#fff";
        ctx.strokeRect((x+offset.x)*BLOCK_SIZE, (y+offset.y)*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE);
      }
    }
  }
}

function getColor(val){
  switch(val){
    case 1: return "#00ffff"; // I
    case 2: return "#ffff00"; // O
    case 3: return "#800080"; // T
    case 4: return "#00ff00"; // S
    case 5: return "#ff0000"; // Z
    case 6: return "#0000ff"; // J
    case 7: return "#ffa500"; // L
    default: return "#cccccc";
  }
}
