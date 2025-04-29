// Simple, reliable loading screen animation
document.addEventListener('DOMContentLoaded', function() {
    // Get loading screen elements
    const loadingScreen = document.getElementById('loading-screen');
    const progressBar = document.getElementById('loading-progress');
    const progressPercent = document.getElementById('progress-percent');
    
    // Make sure elements exist before continuing
    if (!loadingScreen || !progressBar || !progressPercent) {
        console.error('Loading screen elements not found!');
        return;
    }
    
    // Start at a visible percentage
    let progress = 0;
    progressBar.style.width = '0%';
    progressPercent.textContent = '0';
    
    // Fixed increment for reliability
    const interval = setInterval(function() {
        // Use a fixed increment to ensure smooth progress
        progress += 2;
        
        if (progress > 100) {
            progress = 100;
            clearInterval(interval);
            
            // Hide loading screen with fade out
            setTimeout(function() {
                loadingScreen.style.opacity = '0';
                
                // Remove from layout after transition
                setTimeout(function() {
                    loadingScreen.style.display = 'none';
                }, 1000);
            }, 500);
        }
        
        // Update visuals
        progressBar.style.width = progress + '%';
        progressPercent.textContent = progress;
    }, 40); // 40ms for smooth animation
});
