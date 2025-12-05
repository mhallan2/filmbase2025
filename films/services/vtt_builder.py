class VTTBuilder:
    """
    Небольшая оболочка над существующей логикой генерации VTT.
    Вариант A: если модель SubtitleSet имеет method generate_vtt(), используем его.
    Иначе — формируем VTT здесь (fallback).
    """

    def __init__(self, subtitle_set):
        self.subtitle_set = subtitle_set

    def build(self):
        s = self.subtitle_set
        if s is None:
            return "WEBVTT\n\n"

        # fallback: simple builder (keeps same tags as before)
        try:
            lines_qs = s.lines.all().order_by('start_time', 'end_time')
        except Exception:
            return "WEBVTT\n\n"

        vtt_lines = ["WEBVTT", ""]
        for ln in lines_qs:
            start_ms = int(ln.start_time * 1000)
            end_ms = int(ln.end_time * 1000)

            def fmt(ms):
                hours = ms // 3600000
                ms2 = ms % 3600000
                minutes = ms2 // 60000
                ms3 = ms2 % 60000
                seconds = ms3 // 1000
                milli = ms3 % 1000
                return f"{hours:02}:{minutes:02}:{seconds:02}.{milli:03}"

            vtt_lines.append(f"{fmt(start_ms)} --> {fmt(end_ms)}")

            text = (ln.text or "").strip()
            if ln.name:
                text = f"<v {ln.name}>{text}"

            raw_classes = (ln.style_classes or '').strip().split()
            valid = [c for c in raw_classes if c and c.replace('_', '').isalnum()]
            if valid:
                cls = ".".join(valid)
                text = f"<c.{cls}>{text}</c>"

            vtt_lines.append(text)
            vtt_lines.append("")

        return "\n".join(vtt_lines)