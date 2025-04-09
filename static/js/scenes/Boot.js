class Boot extends Phaser.Scene {
    constructor() {
        super('Boot');
    }

    preload() {
        // Cargar assets básicos necesarios para la pantalla de carga
        this.load.image('loading-background', '/assets/images/backgrounds/loading-background.png');
        this.load.image('loading-bar', '/assets/images/ui/loading-bar.png');
    }

    create() {
        this.scene.start('Preload');
    }
} 