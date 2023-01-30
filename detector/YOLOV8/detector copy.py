import torch
import logging
import numpy as np
import cv2
# from .models import *
# from .utils import *
import sys

import utils
from detector.YOLOV8.ultralytics import YOLO

# from models.common import DetectMultiBackend
# from models.experimental import attempt_load
from detector.YOLOV8.utils.general import check_img_size, non_max_suppression, apply_classifier, scale_coords, xyxy2xywh, \
    strip_optimizer, set_logging, increment_path
from detector.YOLOV8.utils.augmentations import letterbox
from detector.YOLOV8.utils.torch_utils import select_device, smart_inference_mode
from detector.YOLOV8.ultralytics.nn.autobackend import AutoBackend
from detector.YOLOV8.ultralytics.yolo.utils import DEFAULT_CONFIG, ROOT, ops
class YOLOv8(object):
    def __init__(self, weightfile="", 
    score_thresh=0.0, conf_thresh=0.25, nms_thresh=0.45,
                 is_xywh=True, use_cuda=True, imgsz=(640, 640),**kwargs):    
        # net definition
        # self.device = "cuda" if use_cuda else "cpu"
        config = kwargs['config']
        DEVICE = config['DEVICE']
        self.device = select_device(DEVICE)
        # self.net = attempt_load(weightfile, map_location=self.device)  # load FP32 model
        OpenCV_DNN = config["OpenCV_DNN"]
        DATA_CONFIG = config["DATA_CONFIG"]
        half = False
        self.net = YOLO(weightfile).model
        source			= "/workspace/py/ultralytics/yolov8/ultralytics/assets"
        iou				= 0.45
        conf			= 0.25
        save_txt		= False
        save_conf		= False
        save_crop		= False
        agnostic_nms	= False
        augment			= False
        visualize		= False
        project			= "/workspace/github/yolovx_deepsort_pytorch/detector/YOLOV8/runs/detect"
        name			= "exp"
        exist_ok		= False
        line_thickness	= 3
        hide_labels		= False
        hide_conf		= False
        half			= False
        dnn				= False
        vid_stride		= False
        retina_masks	= False
        self.max_det    = 300
        self.net = AutoBackend(self.net, device=self.device, dnn=OpenCV_DNN, fp16=half)
        # self.net.predict(source=source, 
        # iou=iou, 
        # conf=conf, 
        # save_txt=save_txt, 
        # save_conf=save_conf,
        # save_crop=save_crop, 
        # agnostic_nms=agnostic_nms, 
        # augment=augment,
        # visualize=visualize, 
        # project=project, 
        # name=name, 
        # exist_ok=exist_ok,
        # line_thickness=line_thickness, 
        # hide_labels=hide_labels, 
        # hide_conf=hide_conf, 
        # half=half, 
        # dnn=dnn,
        # vid_stride=vid_stride, 
        # retina_masks=retina_masks)


          
        # self.net = DetectMultiBackend(weightfile, device=self.device, dnn=OpenCV_DNN, data=DATA_CONFIG, fp16=half)
        self.net.warmup(imgsz=(1, 3, *imgsz))  # warmup
        imgsz = check_img_size(imgsz, s=self.net.stride)  # check img_size
        self.class_names = self.net.module.names if hasattr(self.net, 'module') else self.net.names

        # # constants
        self.size = imgsz 
        self.score_thresh = score_thresh
        self.conf_thresh = conf_thresh
        self.is_xywh = is_xywh          # 未用到
        # self.num_classes = self.net.nc

        self.iou_thres = nms_thresh
    
    def xyxy_to_xywh(self, boxes_xyxy):
        if isinstance(boxes_xyxy, torch.Tensor):
            boxes_xywh = boxes_xyxy.clone()
        elif isinstance(boxes_xyxy, np.ndarray):
            boxes_xywh = boxes_xyxy.copy()

        boxes_xywh[:, 0] = (boxes_xyxy[:, 0] + boxes_xyxy[:, 2]) / 2.
        boxes_xywh[:, 1] = (boxes_xyxy[:, 1] + boxes_xyxy[:, 3]) / 2.
        boxes_xywh[:, 2] = boxes_xyxy[:, 2] - boxes_xyxy[:, 0]
        boxes_xywh[:, 3] = boxes_xyxy[:, 3] - boxes_xyxy[:, 1]

        return boxes_xywh
    
    def check_infer(self):
        from detector.YOLOV8.ultralytics.yolo.data.augment import LetterBox
        from detector.YOLOV8.ultralytics.yolo.engine.predictor import BasePredictor
        # from detector.YOLOV8.ultralytics.yolo.v8.detect.predict import preprocess, postprocess
        from detector.YOLOV8.ultralytics.yolo.utils import DEFAULT_CONFIG, ROOT, ops
                
       
        path = "/workspace/github/yolovx_deepsort_pytorch/detector/YOLOV8/ultralytics/assets/bus.jpg"
        im0 = cv2.imread(path)  # BGR
        im = LetterBox([640, 640], True, 32)(image=im0)
        im = im.transpose((2, 0, 1))[::-1]  # HWC to CHW, BGR to RGB
        im = np.ascontiguousarray(im)  # contiguous     
        im = self.preprocess(im)
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim        
        preds = self.net(im, augment=False,)
        preds = self.postprocess(preds, im, im0)
        
        pass

    def __call__(self, ori_img):
        # self.check_infer()
        # img to tensor
        assert isinstance(ori_img, np.ndarray), "input must be a numpy array!"
        
        # resize
        img = letterbox(ori_img, new_shape=self.size)[0]
        img = img[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB, to 3x416x416
        img = np.ascontiguousarray(img)        
        img = torch.from_numpy(img).float().unsqueeze(0)
        img /=  255.        
        # forward
        with torch.no_grad():
            img = img.to(self.device)
            out_boxes = self.net(img)
            # pred = non_max_suppression(out_boxes, self.conf_thresh, self.iou_thres)
            # pred  = ops.non_max_suppression(out_boxes,
            #                             self.conf_thresh,
            #                             self.iou_thres,
            #                             agnostic=False,     # self.agnostic_nms
            #                             max_det=self.max_det)
            # preds  = ops.non_max_suppression(out_boxes,
            #                             0.25,
            #                             0.45,
            #                             agnostic=False,     # self.agnostic_nms
            #                             max_det=self.max_det)     
                          
            # self.webcam  = False
            # for i, pred in enumerate(preds):
            #     shape = ori_img[i].shape if self.webcam else ori_img.shape
            #     pred[:, :4] = ops.scale_boxes(img.shape[2:], pred[:, :4], shape).round()
            preds = self.postprocess(out_boxes, img, ori_img)

            # detector.YOLOV8.ultralytics.yolo.v8.predict.postprocess
            boxes = preds[0]
            if str(self.score_thresh)  == "0.0":
                pass
            else:
                boxes = boxes[boxes[:, -2] > self.score_thresh, :]  # bbox xmin ymin xmax ymax;     Detections matrix nx6 (xyxy, conf, cls)

        if len(boxes) == 0:
            bbox = torch.FloatTensor([]).reshape([0, 4])
            cls_conf = torch.FloatTensor([])
            cls_ids = torch.LongTensor([])
        else:
            # Rescale boxes from img_size to im0 size
            img_infer = img
            det_box = boxes
            im0_original = ori_img
            # det_box[:, :4] = scale_coords(img_infer.shape[2:], det_box[:, :4], im0_original.shape).round()            
            bbox = det_box[:, :4]
            if self.is_xywh:
                # bbox x y w h
                bbox = self.xyxy_to_xywh(bbox)
                pass
            cls_conf = boxes[:, 4]
            cls_ids = boxes[:, 5].long()
        return bbox.cpu().numpy(), cls_conf.cpu().numpy(), cls_ids.cpu().numpy()

    def load_class_names(self, namesfile):
        with open(namesfile, 'r', encoding='utf8') as fp:
            class_names = [line.strip() for line in fp.readlines()]
        return class_names

    def preprocess(self, img):
        img = torch.from_numpy(img).to(self.device)
        img =  img.float()  # uint8 to fp16/32
        img /= 255  # 0 - 255 to 0.0 - 1.0
        return img
    
    def postprocess(self, preds, img, orig_img):
        preds = ops.non_max_suppression(preds,
                                        0.15,
                                        0.45,
                                        agnostic=False,
                                        max_det=self.max_det)

        for i, pred in enumerate(preds):
            shape =  orig_img.shape
            pred[:, :4] = ops.scale_boxes(img.shape[2:], pred[:, :4], shape).round()

        return preds