import os
import sys
sys.path.insert(0, os.getcwd())

from src.prompts import PROMPT
from src.scorer.intervl3 import InterVL3Scorer
import math


if __name__=='__main__':
    model_path = './storage/vlm/InternVL3_14B'
    num_segments = 2
    video_path = './demo/demo.mp4'
    input_text = 'a person waves a friendly hello.'

    scorer = InterVL3Scorer(model_path=model_path, num_segments=num_segments)
    nrm_label_to_probs = scorer.score(video_path=video_path, prompt=PROMPT.format(input_text=input_text))
    entropy = -sum(p * math.log2(p) for p in nrm_label_to_probs.values() if p > 0)

    print(nrm_label_to_probs)  
    print(entropy)
