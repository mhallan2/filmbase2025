// films/static/films/js/subtitle_sync.js

/**
 * Инициализирует логику синхронизации кастомных субтитров с YouTube-плеером.
 * @param {string} vttUrl - URL для загрузки VTT-файла из Django (который генерируется из БД).
 * @param {string} playerIframeId - ID элемента iframe YouTube плеера ('youtube-player').
 * @param {string} overlayElementId - ID элемента-контейнера для отображения субтитров ('custom-subtitle-overlay').
 */
function initializeSubtitleSync(vttUrl, playerIframeId, overlayElementId) {

    var player;
    var subtitles = [];
    var subtitleOverlay = document.getElementById(overlayElementId);
    var currentCueIndex = -1;
    var updateInterval;

    // ------------------- Вспомогательные функции --------------------

    /**
     * Конвертация VTT времени (00:00:00.000) в секунды (float).
     */
    function timeToSeconds(timeStr) {
        var parts = timeStr.split(/[:,.]/);
        var seconds = 0;
        if (parts.length === 4) {
            seconds += parseInt(parts[0]) * 3600; // Часы
            seconds += parseInt(parts[1]) * 60;   // Минуты
            seconds += parseInt(parts[2]);        // Секунды
            seconds += parseInt(parts[3]) / 1000; // Миллисекунды
        }
        return seconds;
    }

    /**
     * Парсит VTT данные с помощью RegExp (синхронно).
     * Работает надежнее, чем нативный парсер, если VTT-формат не идеален.
     */
    function parseVTT(vttData) {
        var lines = vttData.split('\n');
        var cues = [];
        // Простой и надежный RegEx для таймингов
        var timingRegex = /(\d{2}:\d{2}:\d{2}\.\d{3})\s+-->\s+(\d{2}:\d{2}:\d{2}\.\d{3})\s*(.*)/;

        for (var i = 1; i < lines.length; i++) {
            var timingMatch = lines[i].match(timingRegex);

            if (timingMatch) {
                var startTime = timeToSeconds(timingMatch[1]);
                var endTime = timeToSeconds(timingMatch[2]);
                var classes = timingMatch[3].trim();
                var textLine = lines[i + 1] || '';

                // Пропускаем строки до следующего блока
                while (lines[i] !== undefined && lines[i].trim() !== '' && !lines[i].includes('-->')) {
                    i++;
                }

                cues.push({
                    start: startTime,
                    end: endTime,
                    // Текст с VTT-тегами (<c.speaker> и т.д.)
                    text: textLine.trim(),
                    classes: classes
                });
            }
        }
        console.log("LOG: Синхронный парсер завершен. Найдено строк:", cues.length); // ЛОГ
        return cues;
    }

    /**
     * Форматирует текст VTT-тегов в HTML и оборачивает для фона.
     */
    function formatTextForOverlay(rawText) {
        if (!rawText) return '';

        var htmlText = rawText;

        // 1. Обработка тегов <c.class> -> <span class="class">
        htmlText = htmlText.replace(/<c\.([^>]+)>/g, function(match, classNames) {
        // Теперь classNames определен и содержит список классов, разделенных пробелами.
            return '<span class="' + classNames.trim() + '">';
        });

        htmlText = htmlText.replace(/<\/c>/g, '</span>');

        // 2. Обертываем весь результат в контейнер для стилизации фона (display: inline-block)
        return `<span class="subtitle-line-text">${htmlText}</span>`;
    }

    // ------------------- Логика плеера и синхронизации --------------------

    // Вызывается YouTube API, когда оно загружено
    window.onYouTubeIframeAPIReady = function() {
        var currentOrigin = window.location.protocol + '//' + window.location.host;

        player = new YT.Player(playerIframeId, {
            playerVars: {
                'autoplay': 0,
                'controls': 1,
                'enablejsapi': 1,
                'origin': currentOrigin
            },
            events: {
                'onStateChange': onPlayerStateChange
            }
        });

        // 2. Асинхронная загрузка VTT-данных (получение текста)
        fetch(vttUrl)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.text();
            })
            .then(vttData => {
                console.log("LOG: VTT текст успешно получен. Размер:", vttData.length); // ЛОГ
                // Синхронный парсинг текста
                subtitles = parseVTT(vttData);
            })
            .catch(error => console.error('Ошибка загрузки или парсинга субтитров:', error));
    }

    function onPlayerStateChange(event) {
        if (event.data === YT.PlayerState.PLAYING) {
            console.log("LOG: Плеер начал воспроизведение. Запуск интервала."); // ЛОГ
            updateInterval = setInterval(updateSubtitle, 50);
        } else {
            clearInterval(updateInterval);
        }
    }

    function updateSubtitle() {
        var currentTime = player.getCurrentTime();
        var foundCue = false;

        for (var i = 0; i < subtitles.length; i++) {
            var cue = subtitles[i];

            if (currentTime >= cue.start && currentTime < cue.end) {
                if (i !== currentCueIndex) {
                    currentCueIndex = i;

                    console.log(`LOG: Отображение субтитра #${i}. Время: ${currentTime.toFixed(2)}`); // ЛОГ
                    subtitleOverlay.innerHTML = formatTextForOverlay(cue.text);

                    subtitleOverlay.className = '';
                }
                foundCue = true;
                break;
            }
        }

        if (!foundCue && currentCueIndex !== -1) {
            currentCueIndex = -1;
            subtitleOverlay.textContent = '';
            subtitleOverlay.className = '';
        }
    }

    // Загрузка YouTube Iframe API
    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
}