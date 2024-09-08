// Event listener for file selection
document.getElementById('file-input').addEventListener('change', function(event) {
    const file = event.target.files[0];
    const reader = new FileReader();

    // Load the file and display the preview
    reader.onload = function(e) {
        const preview = document.getElementById('preview');
        const label = document.getElementById('file-label');

        preview.src = e.target.result;
        preview.style.display = 'block';
        label.style.display = 'none';
    };

    reader.readAsDataURL(file);
});

// Event listener for form submission
document.getElementById('upload-form').addEventListener('submit', function(event) {
    // Show the loading screen when the form is submitted
    document.getElementById('loading-screen').style.display = 'flex';
});

// Initial border color for the upload area
document.getElementById('upload-area').style.border = '2px dashed #ffffff';

if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('/service-worker.js')
            .then((registration) => {
                console.log('Service Worker registered with scope:', registration.scope);
            })
            .catch((error) => {
                console.log('Service Worker registration failed:', error);
            });
    });
}