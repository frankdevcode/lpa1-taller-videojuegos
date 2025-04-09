class Boot extends Phaser.Scene {
    constructor() {
        super('Boot');
    }

    preload() {
        // Cargar assets básicos necesarios para la pantalla de carga
        this.load.image('loading-background', '/static/assets/images/backgrounds/loading-background.svg');
        this.load.image('loading-bar', '/static/assets/images/ui/loading-bar.svg');
    }

    create() {
        this.scene.start('Preload');
    }
} 