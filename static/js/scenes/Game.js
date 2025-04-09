class Game extends Phaser.Scene {
    constructor() {
        super('Game');
    }

    create() {
        // Variables del juego
        this.score = 0;
        
        // Agregar fondo
        const bg = this.add.image(0, 0, 'background-dungeon');
        bg.setOrigin(0, 0);
        bg.setDisplaySize(this.cameras.main.width, this.cameras.main.height);
        
        // Crear plataformas
        this.platforms = this.physics.add.staticGroup();
        
        // Plataforma base (suelo)
        this.platforms.create(this.cameras.main.width / 2, this.cameras.main.height - 32, 'button')
            .setScale(20, 2)
            .refreshBody();
        
        // Algunas plataformas flotantes
        this.platforms.create(600, 400, 'button').setScale(4, 0.5).refreshBody();
        this.platforms.create(50, 250, 'button').setScale(4, 0.5).refreshBody();
        this.platforms.create(750, 220, 'button').setScale(4, 0.5).refreshBody();
        
        // Interfaz de usuario
        this.scoreText = this.add.text(16, 16, 'Puntos: 0', { fontSize: '32px', fill: '#fff' });
        
        // Texto de juego incompleto
        const infoText = this.add.text(this.cameras.main.width / 2, this.cameras.main.height / 2, 'Escena de juego en desarrollo', { 
            font: 'bold 32px Arial', 
            fill: '#ffffff',
            stroke: '#000000',
            strokeThickness: 4
        });
        infoText.setOrigin(0.5);
        
        // Botón para volver al menú
        const menuButton = this.add.image(this.cameras.main.width / 2, this.cameras.main.height / 2 + 100, 'button');
        menuButton.setScale(2);
        menuButton.setInteractive();
        
        const menuText = this.add.text(this.cameras.main.width / 2, this.cameras.main.height / 2 + 100, 'Volver al Menú', { 
            font: 'bold 24px Arial', 
            fill: '#ffffff' 
        });
        menuText.setOrigin(0.5);
        
        // Eventos del botón
        menuButton.on('pointerdown', () => {
            this.scene.start('MainMenu');
        });
        
        menuButton.on('pointerover', () => {
            menuButton.setTint(0xcccccc);
        });
        
        menuButton.on('pointerout', () => {
            menuButton.clearTint();
        });
    }
} 