// DOM Elements
const video = document.getElementById('webcam-video');
const canvas = document.getElementById('webcam-canvas');
const ctx = canvas.getContext('2d');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const overlay = document.getElementById('webcam-overlay');
const facesCountWebcam = document.getElementById('webcam-faces-count');

const uploadPlaceholder = document.getElementById('upload-placeholder');
const imageInput = document.getElementById('image-input');
const btnUpload = document.getElementById('btn-upload');
const uploadPreview = document.getElementById('upload-preview');
const loadingIndicator = document.getElementById('loading-indicator');
const facesCountUpload = document.getElementById('upload-faces-count');

// Variables
let stream = null;
let detectionInterval = null;
const API_URL = 'http://localhost:5000/api';

// --- WEBCAM LOGIC ---

// Start Camera
btnStart.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } });
        video.srcObject = stream;
        
        // Wait for video to be ready to match canvas size
        video.onloadedmetadata = () => {
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            overlay.style.display = 'none';
            btnStart.disabled = true;
            btnStop.disabled = false;
            
            // Start detection loop (10 FPS)
            detectionInterval = setInterval(processVideoFrame, 100);
        };
    } catch (err) {
        console.error("Error accessing webcam:", err);
        alert("Could not access camera. Please ensure permissions are granted.");
    }
});

// Stop Camera
btnStop.addEventListener('click', () => {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        video.srcObject = null;
    }
    if (detectionInterval) {
        clearInterval(detectionInterval);
    }
    
    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    overlay.style.display = 'flex';
    btnStart.disabled = false;
    btnStop.disabled = true;
    facesCountWebcam.innerText = '0';
});

// Extract frame, send to API, draw boxes
async function processVideoFrame() {
    if (video.paused || video.ended) return;

    // Create a temporary unseen canvas to grab the frame
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = video.videoWidth;
    tempCanvas.height = video.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(video, 0, 0, tempCanvas.width, tempCanvas.height);
    
    const base64Image = tempCanvas.toDataURL('image/jpeg', 0.8);

    try {
        const response = await fetch(`${API_URL}/detect_frame`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: base64Image })
        });
        
        const data = await response.json();
        
        if (data.faces) {
            // Update UI
            facesCountWebcam.innerText = data.count;
            
            // Clear previous drawings
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            // Draw new bounding boxes
            ctx.strokeStyle = '#22c55e'; // Green
            ctx.lineWidth = 3;
            ctx.fillStyle = 'rgba(34, 197, 94, 0.2)'; // Light green fill
            
            data.faces.forEach(box => {
                ctx.beginPath();
                ctx.rect(box.x, box.y, box.width, box.height);
                ctx.fill();
                ctx.stroke();
                
                // Add tiny label
                ctx.fillStyle = '#22c55e';
                ctx.font = '14px Arial';
                ctx.fillText('Face', box.x, box.y - 5);
                ctx.fillStyle = 'rgba(34, 197, 94, 0.2)'; // reset
            });
        }
    } catch (e) {
        console.error("Frame processing error:", e);
    }
}

// --- UPLOAD LOGIC ---

btnUpload.addEventListener('click', () => {
    imageInput.click();
});

uploadPlaceholder.addEventListener('click', () => {
    imageInput.click();
});

imageInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Show loading
    loadingIndicator.classList.remove('hidden');
    uploadPreview.style.display = 'none';
    uploadPlaceholder.style.display = 'none';
    facesCountUpload.innerText = '0';

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch(`${API_URL}/detect_upload`, {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (data.error) {
            alert(data.error);
        } else {
            // Display result
            uploadPreview.src = data.image;
            uploadPreview.style.display = 'block';
            facesCountUpload.innerText = data.count;
        }
    } catch (err) {
        console.error("Upload error:", err);
        alert("Failed to process image.");
    } finally {
        loadingIndicator.classList.add('hidden');
        imageInput.value = ''; // Reset input
    }
});
