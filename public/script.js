async function initializeApp() {
    if (typeof discordSdk !== 'undefined') {
        const discord = new discordSdk.DiscordSDK("YOUR_BOT_CLIENT_ID_HERE");
        await discord.ready();
        document.getElementById("welcome-text").innerText = `Connected as ${discord.user.username}!`;
    } else {
        document.getElementById("welcome-text").innerText = "Running outside of Discord Client mode.";
    }
}


document.querySelectorAll('.frame-btn').forEach(button => {
    button.addEventListener('click', () => {
        const frame = button.getAttribute('data-frame');
        const overlay = document.getElementById('frame-overlay');
        
        if (frame === 'voidspawn') {
            overlay.style.border = "10px solid #4a00e0"; 
        } else if (frame === 'polaroid') {
            overlay.style.border = "14px solid #fff";
        } else {
            overlay.style.border = "none";
        }
    });
});

initializeApp();