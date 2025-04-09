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
        this.load.image('background-forest', '/static/assets/images/backgrounds/forest.svg');
        this.load.image('background-dungeon', '/static/assets/images/backgrounds/dungeon.svg');
        this.load.image('background-village', '/static/assets/images/backgrounds/village.svg');
        
        // Interfaz
        this.load.image('button', '/static/assets/images/ui/button.svg');
        this.load.image('health-bar', '/static/assets/images/ui/health-bar.svg');
        
        // ... mantener el resto de cargas de assets comentadas por ahora
        /* 
        // Personajes
        this.load.spritesheet('player', '/static/assets/images/characters/player.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        
        // Enemigos
        this.load.spritesheet('enemy-ground', '/static/assets/images/enemies/ground-enemy.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        this.load.spritesheet('enemy-flying', '/static/assets/images/enemies/flying-enemy.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        
        // Objetos
        this.load.image('treasure-chest', '/static/assets/images/objects/treasure-chest.png');
        this.load.image('potion', '/static/assets/images/objects/potion.png');
        this.load.image('bomb', '/static/assets/images/objects/bomb.png');
        this.load.image('coin', '/static/assets/images/objects/coin.png');
        
        // Efectos
        this.load.spritesheet('explosion', '/static/assets/images/effects/explosion.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        this.load.spritesheet('magic', '/static/assets/images/effects/magic.png', { 
            frameWidth: 64, frameHeight: 64 
        });
        
        // Sonidos
        this.load.audio('background-music', '/static/assets/sounds/background-music.mp3');
        this.load.audio('explosion-sound', '/static/assets/sounds/explosion.mp3');
        this.load.audio('coin-sound', '/static/assets/sounds/coin.mp3');
        */
    }

    create() {
        // Comentar las animaciones por ahora ya que no tenemos los spritesheets
        /*
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
        */

        // Iniciar el menú principal
        this.scene.start('MainMenu');
    }
} 