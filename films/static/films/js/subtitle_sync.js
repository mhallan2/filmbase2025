// films/static/films/js/subtitle_sync.js

/**
 * Инициализирует логику синхронизации кастомных субтитров с YouTube-плеером.
 * @param {string} vttUrl - URL для загрузки VTT-файла из Django.
 * @param {string} playerIframeId - ID элемента iframe YouTube плеера ('youtube-player').
 * @param {string} overlayElementId - ID элемента-контейнера для отображения субтитров ('custom-subtitle-overlay').
 */
function initializeSubtitleSync(vttUrl, playerIframeId, overlayElementId) {

    var player;
    var subtitles = [];
    var subtitleElement = document.getElementById(overlayElementId);
    var currentCueIndex = -1;
    var updateInterval;

    // ------------------- Вспомогательные функции --------------------

    // Конвертация VTT времени (00:00:00.000) в секунды
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

    function parseVTT(vttData) {

        var lines = vttData.split('\n');

        var cues = [];

        // Начинаем со второй строки, пропуская "WEBVTT"

        for (var i = 1; i < lines.length; i++) {

            if (lines[i].includes('-->')) {

                var timingLine = lines[i];



                // ИСПРАВЛЕНИЕ: Разбиваем строку по пробелам: [StartTime, '-->', EndTime, Style1, ...]

                var timeParts = timingLine.split(' ');



                // Время начала - первый элемент (индекс 0)

                var startTime = timeToSeconds(timeParts[0].trim());

                // Время окончания - третий элемент (индекс 2)

                var endTime = timeToSeconds(timeParts[2].trim());



                // Классы стилей начинаются с четвертого элемента (индекс 3)

                var classes = timeParts.slice(3).join(' ');



                var textLine = lines[i + 1] || '';

                i++; // Пропускаем строку с текстом

                i++; // Пропускаем пустую строку после субтитра



                cues.push({

                    start: startTime,

                    end: endTime,

                    text: textLine,

                    classes: classes

                });

            }

        }

        return cues;

    }

    // ------------------- Логика плеера и синхронизации --------------------

    // Вызывается YouTube API, когда оно загружено
    window.onYouTubeIframeAPIReady = function() {
        // 1. Инициализация плеера
        player = new YT.Player(playerIframeId, {
            events: {
                'onStateChange': onPlayerStateChange
            }
        });

        // 2. Асинхронная загрузка VTT-данных
        fetch(vttUrl)
            .then(response => response.text())
            .then(data => {
                subtitles = parseVTT(data);
            })
            .catch(error => console.error('Ошибка загрузки субтитров:', error));
    }

    function onPlayerStateChange(event) {
        // 3. Запуск/остановка интервала проверки времени при Play/Pause
        if (event.data === YT.PlayerState.PLAYING) {
            updateInterval = setInterval(updateSubtitle, 100); 
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
                    // Отображение текста
                    subtitleElement.textContent = cue.text.replace(/<.*?>/g, ''); 
                    subtitleElement.className = ''; // Сброс классов
                    
                    // Добавление CSS-классов
                    if (cue.classes) {
                        var cssClasses = cue.classes.split(' ').map(cls => 'cue-' + cls).join(' ');
                        subtitleElement.classList.add(...cssClasses.split(' '));
                    }
                }
                foundCue = true;
                break;
            }
        }

        if (!foundCue && currentCueIndex !== -1) {
            // Субтитр закончился
            currentCueIndex = -1;
            subtitleElement.textContent = '';
            subtitleElement.className = ''; 
        }
    }

    // 5. Загрузка YouTube Iframe API
    var tag = document.createElement('script');
    tag.src = "https://www.youtube.com/iframe_api";
    var firstScriptTag = document.getElementsByTagName('script')[0];
    firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
}
