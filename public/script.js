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

document.getElementById('mirrored-energy-btn').addEventListener('click', () => {
    applyFrame('frame.png'); 
});

document.getElementById('remove-frame-btn').addEventListener('click', () => {
    applyFrame(null);
});

initializeApp();