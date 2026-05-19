#!/usr/bin/env python3
"""
Script to add subtitles and metrics to videos by extending them horizontally.
Creates a mirror of path/to/saved_motion in path/to/extended_demos with extended videos.
"""

import json
from pathlib import Path
from typing import Dict, Any
from moviepy import VideoFileClip, TextClip, CompositeVideoClip, ColorClip


def load_json_data(json_path: Path) -> Dict[str, Any]:
    """Load JSON data from file."""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_vemo_scores(vemo_data: Dict[str, Any], video_id: str) -> Dict[str, float]:
    """Extract VeMo scores from vemo_out data."""
    if video_id not in vemo_data:
        return {}

    scores = vemo_data[video_id].get('score', {})
    internvl_scores = scores.get('InternVL3_14B-n32', {})

    result = {}
    if '0' in internvl_scores:
        result['VeMo (human-opt view)'] = internvl_scores['0']
    if 'stick' in internvl_scores:
        result['VeMo (stick-figure)'] = internvl_scores['stick']

    return result


def get_eval_data(eval_data: Dict[str, Any], video_id: str) -> Dict[str, Any]:
    """Extract revised_text and scores from eval_scores data."""
    if video_id not in eval_data:
        return {}

    entry = eval_data[video_id]
    return {
        'revised_text': entry.get('revised_text', ''),
        'scores': entry.get('score', {})
    }


def format_text_content(revised_text: str, vemo_scores: Dict[str, float], eval_scores: Dict[str, float]) -> str:
    """Format all text content for the side panel. Only show computed metrics."""
    lines = []

    # Add revised text
    if revised_text:
        lines.append("Text:")
        lines.append(revised_text)
        lines.append("")

    # Add metrics header only if we have any metrics
    metrics_lines = []

    # Add VeMo scores (only if they exist and are valid)
    if 'VeMo (human-opt view)' in vemo_scores and vemo_scores['VeMo (human-opt view)'] is not None:
        metrics_lines.append(f"VeMo (human-opt): {vemo_scores['VeMo (human-opt view)']:.3f}")
    if 'VeMo (stick-figure)' in vemo_scores and vemo_scores['VeMo (stick-figure)'] is not None:
        metrics_lines.append(f"VeMo (stick-fig): {vemo_scores['VeMo (stick-figure)']:.3f}")

    # Add other metrics (only if they exist and are valid)
    metric_keys = [
        'R1-Precision', 'R2-Precision', 'R3-Precision',
        'MoBERT-min(F/N)', 'MotionCritic'
    ]

    for key in metric_keys:
        if key in eval_scores and eval_scores[key] is not None:
            metrics_lines.append(f"{key}: {eval_scores[key]:.3f}")

    # Only add metrics section if we have any metrics to show
    if metrics_lines:
        lines.append("Metrics:")
        lines.extend(metrics_lines)

    return '\n'.join(lines)


def create_extended_video(input_video: Path, output_video: Path, text_content: str, text_width: int = 400):
    """Create video with extended horizontal space for text."""
    try:
        # Load original video
        video = VideoFileClip(str(input_video))

        # Create black background for extended area
        text_bg = ColorClip(
            size=(text_width, video.h),
            color=(0, 0, 0),
            duration=video.duration
        )

        # Create text clip for the side panel
        text_clip = TextClip(
            text=text_content,
            font_size=14,
            color='white',
            size=(text_width - 20, video.h - 20),
            method='caption',
            duration=video.duration
        ).with_position((video.w + 10, 10))

        # Position text background
        text_bg = text_bg.with_position((video.w, 0))

        # Composite: original video + text background + text
        final_video = CompositeVideoClip(
            [video, text_bg, text_clip],
            size=(video.w + text_width, video.h)
        )

        # Write output
        final_video.write_videofile(
            str(output_video),
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            logger=None
        )

        # Clean up
        video.close()
        final_video.close()

        return True
    except Exception as e:
        print(f"  Error: {e}")
        return False


def process_model_videos(model_name: str, vemo_data: Dict, eval_data: Dict):
    """Process all videos for a specific model."""
    input_dir = Path(f"path/to/saved_motion/{model_name}")
    output_dir = Path(f"path/to/extended_demos/{model_name}")

    if not input_dir.exists():
        print(f"  Input directory not found: {input_dir}")
        return 0

    processed_count = 0
    video_dirs = sorted([d for d in input_dir.iterdir() if d.is_dir()])

    for video_dir in video_dirs:
        video_id = video_dir.name
        input_video = video_dir / "stick.mp4"

        if not input_video.exists():
            continue

        # Create output directory mirroring input structure
        output_video_dir = output_dir / video_id
        output_video_dir.mkdir(parents=True, exist_ok=True)
        output_video = output_video_dir / "stick.mp4"

        # Get data
        vemo_scores = get_vemo_scores(vemo_data, video_id)
        eval_info = get_eval_data(eval_data, video_id)

        if not eval_info:
            print(f"  Skipping {video_id}: no eval data")
            continue

        revised_text = eval_info.get('revised_text', '')
        eval_scores = eval_info.get('scores', {})

        # Format text content
        text_content = format_text_content(revised_text, vemo_scores, eval_scores)

        print(f"  Processing {video_id}...")
        if create_extended_video(input_video, output_video, text_content):
            processed_count += 1

    return processed_count


def main():
    print("Loading data...")

    # Model names
    models = ['mdm', 'mgpt', 'mld', 'motionlcm', 'real', 'stablemofusion']

    total_processed = 0

    for model in models:
        print(f"\nProcessing {model}...")

        # Load vemo_out data
        vemo_json = Path(f"./storage/vemo_out/saved_motion/{model}_scores.json")
        if not vemo_json.exists():
            print(f"  Skipping: {vemo_json} not found")
            continue

        vemo_data = load_json_data(vemo_json)

        # Load eval_scores data
        eval_json = Path(f"./storage/eval_scores/{model}.json")
        if not eval_json.exists():
            print(f"  Warning: {eval_json} not found, using vemo data only")
            eval_data = {}
        else:
            eval_data = load_json_data(eval_json)

        # Process videos
        count = process_model_videos(model, vemo_data, eval_data)
        total_processed += count
        print(f"  Processed {count} videos")

    print(f"\n{'='*50}")
    print(f"Done! Total videos processed: {total_processed}")


if __name__ == "__main__":
    main()
