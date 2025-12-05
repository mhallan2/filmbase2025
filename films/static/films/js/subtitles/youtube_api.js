/**
 * Загружает YouTube Iframe API, если он ещё не загружен.
 */
export function loadYouTubeAPI() {
    return new Promise((resolve) => {
        if (window.YT && window.YT.Player) {
            resolve(window.YT);
            return;
        }

        const tag = document.createElement('script');
        tag.src = "https://www.youtube.com/iframe_api";
        document.head.appendChild(tag);

        window.onYouTubeIframeAPIReady = () => resolve(window.YT);
    });
}

/**
 * Создаёт объект плеера и возвращает Promise<player>.
 */
export function createYouTubePlayer(iframeId) {
    return new Promise((resolve) => {
        loadYouTubeAPI().then(() => {
            const player = new YT.Player(iframeId, {
                events: {
                    "onReady": () => resolve(player),
                }
            });
        });
    });
}