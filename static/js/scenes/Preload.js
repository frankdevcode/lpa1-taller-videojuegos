class Preload extends Phaser.Scene {
    constructor() {
        super('Preload');
    }

    preload() {
        // Crear barra de carga
        const width = this.cameras.main.width;
        const height = this.cameras.main.height;
        
        // Fondo de carga
        this.add.image(width / 2, height / 2, 'loading-background');
        
        // Barra de progreso
        const progressBar = this.add.graphics();
        const progressBox = this.add.graphics();
        progressBox.fillStyle(0x222222, 0.8);
        progressBox.fillRect(width / 2 - 160, height / 2 - 25, 320, 50);
        
        // Texto de carga
        const loadingText = this.make.text({
            x: width / 2,
            y: height / 2 - 50,
            text: 'Cargando...',
            style: {
                font: '20px monospace',
                fill: '#ffffff'
            }
        });
        loadingText.setOrigin(0.5, 0.5);
        
        // Porcentaje de carga
        const percentText = this.make.text({
            x: width / 2,
            y: height / 2,
            text: '0%',
            style: {
                font: '18px monospace',
                fill: '#ffffff'
            }
        });
        percentText.setOrigin(0.5, 0.5);
        
        // Eventos de carga
        this.load.on('progress', function (value) {
            percentText.setText(parseInt(value * 100) + '%');
            progressBar.clear();
            progressBar.fillStyle(0xffffff, 1);
            progressBar.fillRect(width / 2 - 150, height / 2 - 15, 300 * value, 30);
        });
        
        this.load.on('complete', function () {
            progressBar.destroy();
            progressBox.destroy();
            loadingText.destroy();
            percentText.destroy();
        });
        
        // Cargar todos los assets del juego
        
        // Fondos
        this.load.image('background-forest', '/assets/images/backgrounds/forest.png');
        this.load.image('background-dungeon', '/assets/images/backgrounds/dungeon.png');
        this.load.image('background-village', '/assets/images/backgrounds/village.png');
        
        // Personajes
        this.load.spritesheet('player', '/assets/images/characters/player.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        
        // Enemigos
        this.load.spritesheet('enemy-ground', '/assets/images/enemies/ground-enemy.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        this.load.spritesheet('enemy-flying', '/assets/images/enemies/flying-enemy.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        
        // Objetos
        this.load.image('treasure-chest', '/assets/images/objects/treasure-chest.png');
        this.load.image('potion', '/assets/images/objects/potion.png');
        this.load.image('bomb', '/assets/images/objects/bomb.png');
        this.load.image('coin', '/assets/images/objects/coin.png');
        
        // Efectos
        this.load.spritesheet('explosion', '/assets/images/effects/explosion.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        this.load.spritesheet('magic', '/assets/images/effects/magic.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        
        // Interfaz
        this.load.image('button', '/assets/images/ui/button.png');
        this.load.image('health-bar', '/assets/images/ui/health-bar.png');
        
        // Sonidos
        this.load.audio('background-music', '/assets/sounds/background-music.mp3');
        this.load.audio('explosion-sound', '/assets/sounds/explosion.mp3');
        this.load.audio('coin-sound', '/assets/sounds/coin.mp3');
    }

    create() {
        // Configurar animaciones

        // Animaciones del jugador
        this.anims.create({
            key: 'player-idle',
            frames: this.anims.generateFrameNumbers('player', { start: 0, end: 3 }),
            frameRate: 8,
            repeat: -1
        });

        this.anims.create({
            key: 'player-walk',
            frames: this.anims.generateFrameNumbers('player', { start: 4, end: 9 }),
            frameRate: 10,
            repeat: -1
        });

        this.anims.create({
            key: 'player-attack',
            frames: this.anims.generateFrameNumbers('player', { start: 10, end: 13 }),
            frameRate: 10,
            repeat: 0
        });

        // Animaciones de enemigos
        this.anims.create({
            key: 'enemy-ground-walk',
            frames: this.anims.generateFrameNumbers('enemy-ground', { start: 0, end: 5 }),
            frameRate: 8,
            repeat: -1
        });

        this.anims.create({
            key: 'enemy-flying-fly',
            frames: this.anims.generateFrameNumbers('enemy-flying', { start: 0, end: 5 }),
            frameRate: 8,
            repeat: -1
        });

        // Animaciones de efectos
        this.anims.create({
            key: 'explosion-anim',
            frames: this.anims.generateFrameNumbers('explosion', { start: 0, end: 7 }),
            frameRate: 15,
            repeat: 0
        });

        this.anims.create({
            key: 'magic-anim',
            frames: this.anims.generateFrameNumbers('magic', { start: 0, end: 7 }),
            frameRate: 15,
            repeat: 0
        });

        // Iniciar el menú principal
        this.scene.start('MainMenu');
    }
} 