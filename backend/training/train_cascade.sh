#!/usr/bin/env bash
# Treina o classificador Haar Cascade de impurezas.
#
# Requer os binários opencv_createsamples e opencv_traincascade, que NÃO vêm
# no pacote pip opencv-python 4.x. Opções:
#   - Windows: release oficial OpenCV 3.4.x (build/x64/vc15/bin)
#   - Linux:   compilar OpenCV 3.4.x com -DBUILD_opencv_apps=ON
#
# Uso: ./train_cascade.sh [NUM_POS] [NUM_NEG] [W] [H] [STAGES]
set -euo pipefail

cd "$(dirname "$0")/data"

NUM_POS=${1:-800}
NUM_NEG=${2:-1600}
W=${3:-24}
H=${4:-24}
STAGES=${5:-15}
TOTAL_SAMPLES=$(( NUM_POS * 115 / 100 ))   # folga p/ amostras descartadas por estágio

mkdir -p cascade_out

opencv_createsamples \
  -info positives.dat \
  -vec positives.vec \
  -num "$TOTAL_SAMPLES" \
  -w "$W" -h "$H"

opencv_traincascade \
  -data cascade_out \
  -vec positives.vec \
  -bg bg.txt \
  -numPos "$NUM_POS" \
  -numNeg "$NUM_NEG" \
  -numStages "$STAGES" \
  -featureType HAAR \
  -mode ALL \
  -w "$W" -h "$H" \
  -minHitRate 0.995 \
  -maxFalseAlarmRate 0.5 \
  -precalcValBufSize 2048 \
  -precalcIdxBufSize 2048

cp cascade_out/cascade.xml ../../models/cascade.xml
echo "Modelo copiado para backend/models/cascade.xml"
