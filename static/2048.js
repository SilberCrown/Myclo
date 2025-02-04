// static/2048.js

const GRID_SIZE = 4;         // 4x4
const CELL_SIZE = 100;       // CSS側は80pxだが余白含めて計算
let tiles = [];              // タイル情報を格納 {x, y, value, merged}

let score = 0;

const gridElement = document.getElementById("grid");
const scoreElement = document.getElementById("score");

// 初期化
initGame();
drawTiles();

document.addEventListener("keydown", handleKey);

function handleKey(e) {
  let moved = false;
  if (e.key === "ArrowUp") {
    moved = moveUp();
  } else if (e.key === "ArrowDown") {
    moved = moveDown();
  } else if (e.key === "ArrowLeft") {
    moved = moveLeft();
  } else if (e.key === "ArrowRight") {
    moved = moveRight();
  } else if (e.key === "Escape") {
    resetGame();
  }

  if (moved) {
    spawnTile();
    drawTiles();
  }
}

function initGame() {
  score = 0;
  tiles = [];
  // 2つ初期タイルを出す
  spawnTile();
  spawnTile();
}

function resetGame() {
  score = 0;
  tiles = [];
  initGame();
  drawTiles();
}

function goHome() {
  window.location.href = "/";
}

// 4x4の範囲でランダムな空き枠を探して値2 or 4を配置
function spawnTile() {
  if (tiles.length >= GRID_SIZE*GRID_SIZE) return;

  let freePositions = [];
  for (let y=0; y<GRID_SIZE; y++){
    for (let x=0; x<GRID_SIZE; x++){
      if (!tileAt(x, y)) {
        freePositions.push({x, y});
      }
    }
  }
  if (freePositions.length === 0) return;

  const pos = freePositions[Math.floor(Math.random() * freePositions.length)];
  const val = Math.random() < 0.9 ? 2 : 4;
  tiles.push({x: pos.x, y: pos.y, value: val});
}

function tileAt(x, y) {
  return tiles.find(t => t.x === x && t.y === y);
}

// 描画
function drawTiles() {
  gridElement.innerHTML = "";
  scoreElement.textContent = `Score: ${score}`;

  tiles.forEach(tile => {
    const tileDiv = document.createElement("div");
    tileDiv.classList.add("tile");
    tileDiv.classList.add(`tile-${tile.value}`);
    tileDiv.style.left = (tile.x * 100 + 10) + "px";
    tileDiv.style.top = (tile.y * 100 + 10) + "px";
    tileDiv.textContent = tile.value;
    gridElement.appendChild(tileDiv);
  });
}

/* 移動ロジック (ざっくりした実装)
   moveLeft/moveRight/moveUp/moveDown でタイルを並べ替え、同値なら加算マージ
*/
function moveLeft() {
  let moved = false;
  resetMerged();
  for (let y=0; y<GRID_SIZE; y++){
    // 各行ごとに x=0->3 に詰めて処理
    let rowTiles = tiles.filter(t => t.y === y).sort((a,b) => a.x - b.x);
    moved = compressAndMerge(rowTiles, "x", 0, 1) || moved;
  }
  return moved;
}
function moveRight() {
  let moved = false;
  resetMerged();
  for (let y=0; y<GRID_SIZE; y++){
    let rowTiles = tiles.filter(t => t.y === y).sort((a,b) => b.x - a.x);
    moved = compressAndMerge(rowTiles, "x", GRID_SIZE-1, -1) || moved;
  }
  return moved;
}
function moveUp() {
  let moved = false;
  resetMerged();
  for (let x=0; x<GRID_SIZE; x++){
    let colTiles = tiles.filter(t => t.x === x).sort((a,b) => a.y - b.y);
    moved = compressAndMerge(colTiles, "y", 0, 1) || moved;
  }
  return moved;
}
function moveDown() {
  let moved = false;
  resetMerged();
  for (let x=0; x<GRID_SIZE; x++){
    let colTiles = tiles.filter(t => t.x === x).sort((a,b) => b.y - a.y);
    moved = compressAndMerge(colTiles, "y", GRID_SIZE-1, -1) || moved;
  }
  return moved;
}

function resetMerged() {
  tiles.forEach(t => t.merged = false);
}
function compressAndMerge(lineTiles, axis, start, step) {
  let moved = false;
  let pos = start;
  for (let i=0; i<lineTiles.length; i++){
    const tile = lineTiles[i];
    const oldPos = tile[axis];
    if (oldPos !== pos) {
      tile[axis] = pos;
      moved = true;
    }
    // 次のタイルがあればマージチェック
    if (i < lineTiles.length - 1) {
      const nextTile = lineTiles[i+1];
      if (nextTile[axis] !== (oldPos + step * 1)) {
        // skip, not adjacent
      } else if (tile.value === nextTile.value && !tile.merged && !nextTile.merged) {
        // merge
        tile.value *= 2;
        tile.merged = true;
        score += tile.value;
        // remove nextTile
        tiles.splice(tiles.indexOf(nextTile), 1);
        moved = true;
        i++; // skip next
      }
    }
    pos += step;
  }
  return moved;
}
