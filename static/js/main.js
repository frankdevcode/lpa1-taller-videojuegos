// Inicializar el juego cuando el DOM esté cargado
document.addEventListener('DOMContentLoaded', function() {
    // Crear una nueva instancia del juego
    const game = new Phaser.Game(config);
    
    // Guardar referencia global al juego (para depuración)
    window.game = game;
}); 