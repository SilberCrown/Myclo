// static/mycra.js

const canvas = document.getElementById("mycra-canvas");
const ctx = canvas.getContext("2d");
const infoElem = document.getElementById("info");

const TILE_SIZE = 16; // 1ブロックのピクセル数
const MAP_W = 32;     // x方向のブロック数
const MAP_H = 16;     // y方向のブロック数
const WORLD_WIDTH = MAP_W * TILE_SIZE; 
const WORLD_HEIGHT = MAP_H * TILE_SIZE;

// ブロックID: 0=空、1=草、2=土、3=石 など
let world = [];
let playerX = 0;  // プレイヤー(カメラ)の左上座標
let playerY = 0;

initWorld();
drawWorld();

// キー操作
document.addEventListener("keydown", (e) => {
  switch(e.key) {
    case "a": // 左
      playerX = Math.max(playerX - TILE_SIZE, 0);
      break;
    case "d": // 右
      playerX = Math.min(playerX + TILE_SIZE, WORLD_WIDTH - canvas.width);
      break;
    case "w": // 上
      playerY = Math.max(playerY - TILE_SIZE, 0);
      break;
    case "s": // 下
      playerY = Math.min(playerY + TILE_SIZE, WORLD_HEIGHT - canvas.height);
      break;
    case "Escape":
      resetWorld();
      break;
  }
  drawWorld();
});

// マウスクリック(左クリック)でブロック破壊or設置
canvas.addEventListener("mousedown", (e) => {
  if(e.button === 0) { // Left button
    // Canvas上のクリック座標 → ワールド座標
    const rect = canvas.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const wx = playerX + cx;
    const wy = playerY + cy;

    const bx = Math.floor(wx / TILE_SIZE);
    const by = Math.floor(wy / TILE_SIZE);

    if(bx >= 0 && bx < MAP_W && by >= 0 && by < MAP_H) {
      // クリックしたブロックID
      let blockID = world[by][bx];
      if(blockID === 0) {
        // 空なら 土(2)を置く(例)
        world[by][bx] = 2;
      } else {
        // 何かあれば 0=空に(破壊)
        world[by][bx] = 0;
      }
      drawWorld();
    }
  }
});

function initWorld() {
  // 2次元配列 [y][x] を作る
  world = [];
  for (let y=0; y<MAP_H; y++){
    let row = [];
    for (let x=0; x<MAP_W; x++){
      // 簡易地形生成
      // y < 3 → 空(0)
      // y=3 → 草(1)
      // y>3 ~ y< MAP_H-2 → 土(2)
      // それ以降は石(3)
      if (y < 3) {
        row.push(0); // 空
      } else if (y === 3) {
        row.push(1); // 草
      } else if (y < MAP_H-2) {
        // 土 or 石
        // ランダムで混ぜる
        row.push(Math.random() < 0.8 ? 2 : 3);
      } else {
        row.push(3); // 石
      }
    }
    world.push(row);
  }
  playerX = 0;
  playerY = 0;
}

function resetWorld() {
  initWorld();
  drawWorld();
}

function drawWorld() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 可視範囲のタイルだけ描画
  const startX = Math.floor(playerX / TILE_SIZE);
  const startY = Math.floor(playerY / TILE_SIZE);
  const endX = Math.ceil((playerX + canvas.width) / TILE_SIZE);
  const endY = Math.ceil((playerY + canvas.height) / TILE_SIZE);

  for (let y = startY; y < endY; y++){
    for (let x = startX; x < endX; x++){
      if (y < 0 || y >= MAP_H || x < 0 || x >= MAP_W) continue;

      let blockID = world[y][x];
      if (blockID !== 0) {
        // 描画先
        const drawX = (x * TILE_SIZE) - playerX;
        const drawY = (y * TILE_SIZE) - playerY;
        
        // ブロック色分け
        let color = "#888";
        switch(blockID){
          case 1: color = "#0c0"; break; // 草
          case 2: color = "#964B00"; break; // 土
          case 3: color = "#555"; break; // 石
        }
        ctx.fillStyle = color;
        ctx.fillRect(drawX, drawY, TILE_SIZE, TILE_SIZE);
        // 枠線
        ctx.strokeStyle = "#222";
        ctx.strokeRect(drawX, drawY, TILE_SIZE, TILE_SIZE);
      }
    }
  }

  // プレイヤー位置のdebug
  infoElem.textContent = `XYZ: (${playerX}, ${playerY})`;
}

function goHome() {
  window.location.href = "/";
}
