from ultralytics import YOLO
import torch

def train(model, yaml_path='datasets/data.yaml', epochs=10):
    print(f'Training on {"gpu" if torch.cuda.is_available() else "cpu"}')
    model.train(data=yaml_path, epochs=epochs, imgsz=640, device=0)


if __name__ == '__main__':
    weigths = 'seg_models/yolov8s-seg.pt'  # 'heads_weights.pt' if we need to continue training
    seg_model = YOLO(weigths)
    train(seg_model)

