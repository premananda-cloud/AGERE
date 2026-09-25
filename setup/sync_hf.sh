#!/bin/bash
set -e

echo "🔄 Downloading from kiliez/AGERE_weights..."
# Downloads everything into the 'model' directory
hf download kiliez/AGERE_weights --local-dir model

echo "📂 Routing TensorBoard logs to tb_logs/..."
mkdir -p tb_logs

# Move the actual log directories directly to tb_logs/
[ -d "model/hover_logs" ] && mv model/hover_logs tb_logs/
[ -d "model/waypoint_logs" ] && mv model/waypoint_logs tb_logs/

echo "🧹 Cleaning up stray artifacts..."
# Clean up the accidental 'model' folder and misplaced files inside tb_logs/ 
# left over from previous manual 'mv model tb_logs/' mistakes
rm -rf tb_logs/model
rm -rf tb_logs/model_weights
rm -f tb_logs/README.md

echo "✅ Sync complete!"
echo "   Weights are in: model/model_weights/"
echo "   Logs are in:    tb_logs/hover_logs/"
