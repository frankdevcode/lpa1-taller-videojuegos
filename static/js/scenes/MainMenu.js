class MainMenu extends Phaser.Scene {
    constructor() {
        super('MainMenu');
    }

    create() {
        // Agregar fondo
        const bg = this.add.image(0, 0, 'background-forest');
        bg.setOrigin(0, 0);
        bg.setDisplaySize(this.cameras.main.width, this.cameras.main.height);
        
        // Agregar título
        const title = this.add.text(this.cameras.main.width / 2, 100, 'Aventura Fantástica', { 
            font: 'bold 64px Arial', 
            fill: '#ffffff',
            stroke: '#000000',
            strokeThickness: 6
        });
        title.setOrigin(0.5);
        
        // Agregar botones
        const playButton = this.add.image(this.cameras.main.width / 2, 300, 'button');
        playButton.setScale(2);
        playButton.setInteractive();
        
        const playText = this.add.text(this.cameras.main.width / 2, 300, 'Jugar', { 
            font: 'bold 32px Arial', 
            fill: '#ffffff' 
        });
        playText.setOrigin(0.5);
        
        const optionsButton = this.add.image(this.cameras.main.width / 2, 400, 'button');
        optionsButton.setScale(2);
        optionsButton.setInteractive();
        
        const optionsText = this.add.text(this.cameras.main.width / 2, 400, 'Opciones', { 
            font: 'bold 32px Arial', 
            fill: '#ffffff' 
        });
        optionsText.setOrigin(0.5);
        
        const creditsButton = this.add.image(this.cameras.main.width / 2, 500, 'button');
        creditsButton.setScale(2);
        creditsButton.setInteractive();
        
        const creditsText = this.add.text(this.cameras.main.width / 2, 500, 'Créditos', { 
            font: 'bold 32px Arial', 
            fill: '#ffffff' 
        });
        creditsText.setOrigin(0.5);
        
        // Agregar eventos de los botones
        playButton.on('pointerdown', () => {
            this.scene.start('Game');
        });
        
        // Agregar música de fondo
        if (!this.sound.get('background-music')) {
            const music = this.sound.add('background-music', {
                volume: 0.5,
                loop: true
            });
            music.play();
        }
        
        // Efecto de hover para los botones
        [playButton, optionsButton, creditsButton].forEach(button => {
            button.on('pointerover', () => {
                button.setTint(0xcccccc);
            });
            
            button.on('pointerout', () => {
                button.clearTint();
            });
        });
    }
} 