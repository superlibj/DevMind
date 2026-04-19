// 游戏常量
const GRID_SIZE = 20;
const CELL_SIZE = 20;
const CANVAS_WIDTH = 600;
const CANVAS_HEIGHT = 400;
const GRID_WIDTH = CANVAS_WIDTH / CELL_SIZE;
const GRID_HEIGHT = CANVAS_HEIGHT / CELL_SIZE;

// 游戏状态
let snake = [
    {x: 10, y: 10},
    {x: 9, y: 10},
    {x: 8, y: 10}
];
let food = {x: 15, y: 15};
let direction = 'right';
let nextDirection = 'right';
let gameRunning = false;
let gamePaused = false;
let score = 0;
let highScore = 0;
let gameInterval;
let gameSpeed = 150;

// DOM 元素
const canvas = document.getElementById('game-canvas');
const ctx = canvas.getContext('2d');
const scoreElement = document.getElementById('score');
const highScoreElement = document.getElementById('high-score');
const speedElement = document.getElementById('speed');
const finalScoreElement = document.getElementById('final-score');
const gameOverElement = document.getElementById('game-over');
const startButton = document.getElementById('start-btn');
const pauseButton = document.getElementById('pause-btn');
const resetButton = document.getElementById('reset-btn');
const restartButton = document.getElementById('restart-btn');
const speedSelect = document.getElementById('speed-select');
const gridToggle = document.getElementById('grid-toggle');
const themeSelect = document.getElementById('theme-select');
const soundToggle = document.getElementById('sound-toggle');

// 颜色主题
const themes = {
    dark: {
        background: '#1a1a1a',
        grid: '#333',
        snake: '#4CAF50',
        snakeHead: '#45a049',
        food: '#ff4444',
        text: '#fff'
    },
    light: {
        background: '#f5f5f5',
        grid: '#ddd',
        snake: '#2196F3',
        snakeHead: '#1976D2',
        food: '#FF9800',
        text: '#333'
    },
    neon: {
        background: '#0a0a0a',
        grid: '#222',
        snake: '#00ff00',
        snakeHead: '#00cc00',
        food: '#ff00ff',
        text: '#00ffff'
    }
};

let currentTheme = 'dark';
let soundEnabled = true;

// More content follows...