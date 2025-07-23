import cv2
from ultralytics import YOLO
import numpy as np
from collections import defaultdict
import subprocess
import os

# Load YOLOv10x model
model = YOLO('yolov10x.pt')
cap = cv2.VideoCapture('input_video.mp4')

# Video properties
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps = cap.get(cv2.CAP_PROP_FPS)
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter('output_video.mp4', fourcc, fps, (width, height))

# Define central rectangular ROI
roi_margin_x = int(width * 0.3)
roi_margin_y = int(height * 0.3)
roi_polygon = np.array([
    [roi_margin_x, roi_margin_y],
    [width - roi_margin_x, roi_margin_y],
    [width - roi_margin_x, height - roi_margin_y],
    [roi_margin_x, height - roi_margin_y]
])

# Utilities
def draw_roi(frame, polygon):
    cv2.polylines(frame, [polygon], isClosed=True, color=(255, 0, 0), thickness=3)

def point_in_polygon(point, polygon):
    return cv2.pointPolygonTest(polygon, point, False) >= 0

def draw_shadow_text(frame, text, position, font_scale=1, color=(0, 255, 255)):
    # Shadow
    cv2.putText(frame, text, (position[0] + 2, position[1] + 2), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), 4, lineType=cv2.LINE_AA)
    # Main text
    cv2.putText(frame, text, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2, lineType=cv2.LINE_AA)

# Tracking structures
roi_tracker_id_map = {}                # Only for IDs that entered ROI
next_sequential_id = 1
centroid_history = defaultdict(list)
inflow_ids = set()
outflow_ids = set()
inside_roi_flags = defaultdict(lambda: False)  # Track whether the person was ever inside

while True:
    success, frame = cap.read()
    if not success:
        break

    draw_roi(frame, roi_polygon)

    results = model.track(frame, persist=True, tracker='bytetrack.yaml', classes=[0])
    if results and hasattr(results[0], 'boxes') and results[0].boxes is not None:
        for box in results[0].boxes:
            if hasattr(box, 'id') and box.cls == 0:
                original_id = int(box.id)
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                center_point = (cx, cy)

                centroid_history[original_id].append(center_point)

                # Track entry into ROI
                currently_inside = point_in_polygon(center_point, roi_polygon)
                previously_inside = inside_roi_flags[original_id]

                if not previously_inside and currently_inside:
                    inflow_ids.add(original_id)
                    inside_roi_flags[original_id] = True

                    # Assign display ID only when person enters ROI
                    if original_id not in roi_tracker_id_map:
                        roi_tracker_id_map[original_id] = next_sequential_id
                        next_sequential_id += 1

                elif previously_inside and not currently_inside:
                    outflow_ids.add(original_id)
                    inside_roi_flags[original_id] = False  # Person left ROI

                # Only draw + count if inside ROI and has a display ID
                if currently_inside and original_id in roi_tracker_id_map:
                    display_id = roi_tracker_id_map[original_id]
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"Person {display_id:02d}", (x1, y1 - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Calculate people currently inside ROI
    currently_inside_ids = inflow_ids - outflow_ids

    # Draw final counts
    info_text = f"In: {len(inflow_ids)}  Out: {len(outflow_ids)}  Inside: {len(currently_inside_ids)}"
    draw_shadow_text(frame, info_text, (30, height - 30), font_scale=1.1, color=(0, 255, 255))

    out.write(frame)
    cv2.imshow('People Counting (ROI Only)', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
out.release()
cv2.destroyAllWindows()

print(f"✅ Output saved as: output_video.mp4")
print(f"✅ Inflow: {len(inflow_ids)} | Outflow: {len(outflow_ids)} | Currently Inside: {len(inflow_ids - outflow_ids)}")

# FFmpeg Post-processing
input_path = "output_video.mp4"
temp_output_path = "fixed_output.mp4"
ffmpeg_cmd = [
    "ffmpeg", "-y",
    "-i", input_path,
    "-c:v", "libx264",
    "-pix_fmt", "yuv420p",
    "-crf", "23",
    "-preset", "fast",
    temp_output_path
]

try:
    subprocess.run(ffmpeg_cmd, check=True)
    os.replace(temp_output_path, input_path)
    print(f"✅ FFmpeg fixed video: {input_path}")
except subprocess.CalledProcessError as e:
    print("❌ FFmpeg failed:", e)
