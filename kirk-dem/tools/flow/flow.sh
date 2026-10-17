#!/usr/bin/env bash
# Kırk Dem — Flow çıktılarını Unity'ye hazırlayan araçlar (docs/02-sanat-kitabi/flow-oyun-ici-varliklar.md §4).
# Gereken: ffmpeg ve ffprobe (4.3+; xfade için).
#
#   flow.sh strip-audio <girdi.mp4> <çıktı.mp4>
#       Veo'nun ürettiği sesi atar. Oyunda yapay ses yok (dünya kitabı); her klip bundan geçer.
#   flow.sh loop <girdi.mp4> <çıktı.mp4> [geçiş_sn=1]
#       Klibin sonunu başına çapraz geçişle bağlar; çıktı dikişsiz döner. Süre = girdi − geçiş.
#   flow.sh flipbook <girdi.mp4> <çıktı.png> [sütun=8] [satır=8] [hücre_px=256]
#       Klipten eşit aralıklı sütun×satır kare alır, ortadan kare kırpar, tek bir doku atlasına dizer.
#   flow.sh edge-fade <girdi.png> <çıktı.png> [kenar_px=160] [üst_px=0]
#       Arka plan kartının sol ve sağ (isteğe bağlı üst) kenarını saydamlığa yumuşatır; kartlar dikişsiz üst üste biner.
#   flow.sh luma <dosya> [alt_%] [üst_%]
#       Ortalama parlaklığı yüzde olarak yazar; aralık verilirse dışındaysa 1 ile çıkar.

set -euo pipefail

die() { echo "flow.sh: $*" >&2; exit 2; }
need() { command -v "$1" >/dev/null 2>&1 || die "$1 bulunamadı"; }
need ffmpeg; need ffprobe

duration() { ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$1"; }

cmd="${1:-}"; shift || true
case "$cmd" in
  strip-audio)
    [ $# -eq 2 ] || die "kullanım: strip-audio <girdi> <çıktı>"
    ffmpeg -v error -y -i "$1" -map 0:v:0 -c:v copy -an "$2"
    ;;
  loop)
    [ $# -ge 2 ] || die "kullanım: loop <girdi> <çıktı> [geçiş_sn]"
    in="$1"; out="$2"; f="${3:-1}"
    d=$(duration "$in")
    off=$(awk -v d="$d" -v f="$f" 'BEGIN { o = d - 2*f; if (o <= 0) exit 1; printf "%.3f", o }') \
      || die "klip çok kısa: süre ${d} sn, geçiş ${f} sn (süre > 2×geçiş olmalı)"
    ffmpeg -v error -y -i "$in" -filter_complex \
      "[0:v]split[a][b];[a]trim=start=${f},setpts=PTS-STARTPTS[main];[b]trim=0:${f},setpts=PTS-STARTPTS[head];[main][head]xfade=transition=fade:duration=${f}:offset=${off},format=yuv420p[v]" \
      -map "[v]" -an -c:v libx264 -crf 16 -preset slow "$out"
    ;;
  flipbook)
    [ $# -ge 2 ] || die "kullanım: flipbook <girdi> <çıktı.png> [sütun] [satır] [hücre_px]"
    in="$1"; out="$2"; c="${3:-8}"; r="${4:-8}"; px="${5:-256}"
    d=$(duration "$in")
    n=$((c * r))
    rate=$(awk -v n="$n" -v d="$d" 'BEGIN { printf "%.6f", n / d }')
    ffmpeg -v error -y -i "$in" -vf \
      "fps=${rate},crop='min(iw,ih)':'min(iw,ih)',scale=${px}:${px}:flags=lanczos,tile=${c}x${r}" \
      -frames:v 1 -update 1 "$out"
    ;;
  edge-fade)
    [ $# -ge 2 ] || die "kullanım: edge-fade <girdi.png> <çıktı.png> [kenar_px] [üst_px]"
    in="$1"; out="$2"; e="${3:-160}"; t="${4:-0}"
    if [ "$t" -gt 0 ]; then
      a="255*min(1,min(X,W-1-X)/${e})*min(1,Y/${t})"
    else
      a="255*min(1,min(X,W-1-X)/${e})"
    fi
    ffmpeg -v error -y -i "$in" -vf "format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='${a}'" -frames:v 1 -update 1 "$out"
    ;;
  luma)
    [ $# -ge 1 ] || die "kullanım: luma <dosya> [alt_%] [üst_%]"
    f="$1"; lo="${2:-}"; hi="${3:-}"
    avg=$(ffmpeg -v error -i "$f" -vf "format=gray,signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-" -f null - \
          | awk -F= '/YAVG/ { s += $2; n++ } END { if (n) printf "%.1f", (s / n) / 255 * 100 }')
    [ -n "$avg" ] || die "parlaklık ölçülemedi: $f"
    if [ -n "$lo" ] && [ -n "$hi" ]; then
      if awk -v a="$avg" -v l="$lo" -v h="$hi" 'BEGIN { exit !(a >= l && a <= h) }'; then
        echo "$f: ortalama parlaklık %${avg} (aralık %${lo}–%${hi}) UYGUN"
      else
        echo "$f: ortalama parlaklık %${avg} (aralık %${lo}–%${hi}) DIŞINDA"; exit 1
      fi
    else
      echo "$f: ortalama parlaklık %${avg}"
    fi
    ;;
  *)
    sed -n '2,17p' "$0" | sed 's/^# \{0,1\}//'
    [ -z "$cmd" ] || exit 2
    ;;
esac
