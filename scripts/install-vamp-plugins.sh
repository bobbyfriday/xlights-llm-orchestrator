#!/usr/bin/env bash
# Build the three VAMP plugin libraries the audio analyzer REQUIRES, from source, for Linux:
#   qm-vamp-plugins (tempo, bar/beat, key, onsets, tonal change), nnls-chroma (chordino),
#   segmentino (structure). None are packaged by apt.
#
# The compile recipe mirrors the upstream Vamp Plugin Pack's qmake projects
# (github.com/vamp-plugins/vamp-plugin-pack: qm-vamp-plugins.pro, nnls-chroma.pro,
# segmentino.pro, plugin.pri) as plain gcc/g++ calls, so it needs only build-essential, git,
# and the header-only Boost (libboost-dev; nnls-chroma uses boost/tokenizer).
# Used by docker/audio-analysis.Dockerfile and by scripts/setup-cloud-audio.sh.
#
#   VAMP_PREFIX=/usr/local/lib/vamp  install dir (on the vamp host's default Linux search path)
#   QM_REF / NNLS_REF / SEGMENTINO_REF / SDK_REF   git refs to build (defaults below)
#
# Needs network access to github.com.
set -euo pipefail

PREFIX="${VAMP_PREFIX:-/usr/local/lib/vamp}"
QM_REF="${QM_REF:-qm-vamp-plugins-v1.8.0}"     # also pins qm-dsp (same tag, as the pack does)
NNLS_REF="${NNLS_REF:-}"                       # empty = default branch
SEGMENTINO_REF="${SEGMENTINO_REF:-}"
SDK_REF="${SDK_REF:-}"
JOBS="${JOBS:-$(nproc 2>/dev/null || echo 2)}"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
cd "$WORK"

clone() {   # clone <repo> <dest> [ref]
  if [ -n "${3:-}" ]; then
    git clone -q --depth 1 --branch "$3" "https://github.com/$1" "$2"
  else
    git clone -q --depth 1 "https://github.com/$1" "$2"
  fi
}

echo "fetching sources…"
clone c4dm/vamp-plugin-sdk   vamp-plugin-sdk "$SDK_REF"
clone c4dm/qm-vamp-plugins   qm-vamp-plugins "$QM_REF"
clone c4dm/qm-dsp            qm-vamp-plugins/lib/qm-dsp "$QM_REF"
clone c4dm/nnls-chroma       nnls-chroma "$NNLS_REF"
clone c4dm/segmentino        segmentino "$SEGMENTINO_REF"

QMDSP=qm-vamp-plugins/lib/qm-dsp
COMMON_FLAGS=(-O3 -fPIC -w -I"$WORK" -Ivamp-plugin-sdk -Dkiss_fft_scalar=double)
LDFLAGS=(-shared -Wl,--version-script=vamp-plugin-sdk/skeleton/vamp-plugin.map -Wl,-no-undefined)

build() {   # build <name> <extra-flags-var> <sources…>
  local name="$1" extra_var="$2"; shift 2
  local -n extra="$extra_var"
  local objdir="obj/$name"; mkdir -p "$objdir"
  local objs=() cmds=()
  echo "building $name ($# sources)…"
  for src in "$@"; do
    local obj="$objdir/$(echo "$src" | tr '/' '_').o"
    objs+=("$obj")
    case "$src" in
      *.c) cmds+=("gcc ${COMMON_FLAGS[*]} ${extra[*]} -c $src -o $obj") ;;
      *)   cmds+=("g++ -std=c++14 ${COMMON_FLAGS[*]} ${extra[*]} -c $src -o $obj") ;;
    esac
  done
  # compile in parallel; the loop above must NOT be piped (a piped loop runs in a subshell
  # and its objs+= are lost — the link then silently produces an empty library)
  printf '%s\n' "${cmds[@]}" | xargs -P "$JOBS" -I{} sh -c '{}'
  local libs=(); [ "$name" = qm-vamp-plugins ] && libs=(-lpthread)
  g++ "${LDFLAGS[@]}" -o "out/$name.so" "${objs[@]}" "${libs[@]}"
}
mkdir -p out

QM_FLAGS=(-I"$QMDSP" -I"$QMDSP/ext/kissfft" -I"$QMDSP/ext/kissfft/tools"
          -I"$QMDSP/ext/clapack/include" -I"$QMDSP/ext/cblas/include"
          -DNO_BLAS_WRAP -DADD_ -DUSE_PTHREADS)
build qm-vamp-plugins QM_FLAGS \
  qm-vamp-plugins/g2cstubs.c qm-vamp-plugins/libmain.cpp \
  qm-vamp-plugins/plugins/{AdaptiveSpectrogram,BarBeatTrack,BeatTrack,DWT,OnsetDetect,ChromagramPlugin,ConstantQSpectrogram,KeyDetect,MFCCPlugin,SegmenterPlugin,SimilarityPlugin,TonalChangeDetect,Transcription}.cpp \
  $QMDSP/base/{Pitch,KaiserWindow,SincWindow}.cpp \
  $QMDSP/dsp/chromagram/{Chromagram,ConstantQ}.cpp \
  $QMDSP/dsp/keydetection/GetKeyMode.cpp $QMDSP/dsp/mfcc/MFCC.cpp \
  $QMDSP/dsp/onsets/{DetectionFunction,PeakPicking}.cpp \
  $QMDSP/dsp/phasevocoder/PhaseVocoder.cpp \
  $QMDSP/dsp/rateconversion/{Decimator,DecimatorB,Resampler}.cpp \
  $QMDSP/dsp/rhythm/BeatSpectrum.cpp \
  $QMDSP/dsp/segmentation/{cluster_melt.c,ClusterMeltSegmenter.cpp,cluster_segmenter.c,Segmenter.cpp} \
  $QMDSP/dsp/signalconditioning/{DFProcess,Filter,FiltFilt,Framer}.cpp \
  $QMDSP/dsp/tempotracking/{DownBeat,TempoTrack,TempoTrackV2}.cpp \
  $QMDSP/dsp/tonal/{ChangeDetectionFunction,TCSgram,TonalEstimator}.cpp \
  $QMDSP/dsp/transforms/{DCT,FFT}.cpp $QMDSP/dsp/wavelet/Wavelet.cpp \
  $QMDSP/hmm/hmm.c \
  $QMDSP/maths/{Correlation,CosineDistance,KLDivergence,MathUtilities}.cpp $QMDSP/maths/pca/pca.c \
  $QMDSP/thread/Thread.cpp \
  $QMDSP/ext/kissfft/kiss_fft.c $QMDSP/ext/kissfft/tools/kiss_fftr.c \
  $QMDSP/ext/clapack/src/{dgetrf,dgetri,dgetf2,xerbla,dlaswp,dtrtri,ilaenv,iparmq,s_cat,s_copy,s_cmp,pow_di,ieeeck,i_nint,dtrti2,f77_aloc,exit_}.c \
  $QMDSP/ext/cblas/src/{dgemm,ddot,dgemv,dswap,dtrsm,dger,idamax,dscal,dtrmm,lsame,dlamch,dtrmv,cblas_globals,cblas_dgemm,cblas_ddot,cblas_xerbla}.c \
  vamp-plugin-sdk/src/vamp-sdk/{PluginAdapter,RealTime}.cpp

NNLS_FLAGS=(-Innls-chroma)
build nnls-chroma NNLS_FLAGS \
  nnls-chroma/{chromamethods,NNLSBase,NNLSChroma,Chordino,Tuning,plugins,viterbi}.cpp nnls-chroma/nnls.c \
  vamp-plugin-sdk/src/vamp-sdk/{FFT,PluginAdapter,RealTime}.cpp

SEG_FLAGS=(-Iqm-vamp-plugins/lib -I"$QMDSP" -I"$QMDSP/ext/kissfft" -I"$QMDSP/ext/kissfft/tools"
           -Isegmentino/armadillo-3.900.4/include -Innls-chroma)
build segmentino SEG_FLAGS \
  segmentino/segmentino/{Segmentino,libmain}.cpp \
  nnls-chroma/chromamethods.cpp nnls-chroma/nnls.c \
  vamp-plugin-sdk/src/vamp-sdk/{PluginAdapter,RealTime}.cpp \
  $QMDSP/dsp/onsets/{DetectionFunction,PeakPicking}.cpp $QMDSP/dsp/transforms/FFT.cpp \
  $QMDSP/dsp/rateconversion/Decimator.cpp $QMDSP/dsp/tempotracking/{TempoTrackV2,DownBeat}.cpp \
  $QMDSP/dsp/phasevocoder/PhaseVocoder.cpp \
  $QMDSP/dsp/signalconditioning/{DFProcess,FiltFilt,Filter}.cpp \
  $QMDSP/maths/MathUtilities.cpp \
  $QMDSP/ext/kissfft/kiss_fft.c $QMDSP/ext/kissfft/tools/kiss_fftr.c

mkdir -p "$PREFIX"
cp out/*.so "$PREFIX/"
bad=0
for so in out/*.so; do   # capture first: `nm | grep -q` under pipefail fails on SIGPIPE
  syms="$(nm -D --defined-only "$so")"
  if grep -q '^[0-9a-f]* T vampGetPluginDescriptor$' <<<"$syms"; then
    echo "$so: exports vampGetPluginDescriptor"
  else
    bad=1
    name="$(basename "$so" .so)"
    echo "$so exports no vampGetPluginDescriptor; where it is defined in the objects:" >&2
    for o in obj/"$name"/*.o; do
      hits="$(nm -C "$o" | grep -i 'vampGetPluginDescriptor' || true)"
      [ -n "$hits" ] && echo "  $o: $hits" >&2
    done
    echo "  dynamic symbols matching 'Descriptor': $(grep -i descriptor <<<"$syms" | head -5 || true)" >&2
  fi
done
[ "$bad" -eq 0 ] || exit 1
for d in qm-vamp-plugins nnls-chroma segmentino; do
  cp "$d"/*.cat "$d"/*.n3 "$PREFIX/" 2>/dev/null || true
done
echo "installed to $PREFIX:"; ls -1 "$PREFIX"
