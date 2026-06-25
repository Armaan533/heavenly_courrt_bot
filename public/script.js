async function initializeApp() {
    if (typeof discordSdk !== 'undefined') {
        try {
            const discord = new discordSdk.DiscordSDK("1469329087431446578");
            await discord.ready();
            document.getElementById("welcome-text").innerText = `Connected as ${discord.user.username}!`;
        } catch (error) {
            document.getElementById("welcome-text").innerText = "Running outside of Discord Client mode.";
        }
    } else {
        document.getElementById("welcome-text").innerText = "Running outside of Discord Client mode.";
    }
}

const frameOverlay = document.getElementById('frame-overlay');

function applyFrame(frameImageUrl) {
    if (!frameImageUrl) {
        frameOverlay.classList.add('hidden');
        frameOverlay.src = "";
    } else {
        frameOverlay.src = frameImageUrl;
        frameOverlay.classList.remove('hidden');
    }
}

async function loadFrames() {
    try {
        const response = await fetch('frames.json');
        const frames = await response.json();
        
        const controlsArea = document.getElementById('frame-grid');
        controlsArea.innerHTML = ''; 
        
        frames.forEach(frame => {
            const btn = document.createElement('button');
            btn.className = 'frame-btn';
            btn.innerHTML = `${frame.name} <br><small>(${frame.price} 🎟️)</small>`;
            
            btn.addEventListener('click', () => {
                applyFrame(frame.image);
            });
            
            controlsArea.appendChild(btn);
        });
        
    } catch (error) {
        console.error("Error loading frames:", error);
        document.getElementById('frame-grid').innerHTML = "<p>Failed to load frame database.</p>";
    }
}

document.getElementById('remove-frame-btn').addEventListener('click', () => {
    applyFrame(null);
});

initializeApp();
loadFrames();