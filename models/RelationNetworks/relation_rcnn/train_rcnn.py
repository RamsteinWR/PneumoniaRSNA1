# --------------------------------------------------------
# Relation Networks for Object Detection
# Copyright (c) 2017 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Modified by Jiayuan Gu, Dazhi Cheng, Yuwen Xiong
# --------------------------------------------------------
# Based on:
# MX-RCNN
# Copyright (c) 2016 by Contributors
# Licence under The Apache 2.0 License
# https://github.com/ijkguo/mx-rcnn/
# --------------------------------------------------------

import argparse
import logging
import os
import sys

from config.config import config, update_config


def parse_args():
    parser = argparse.ArgumentParser(description='Train Faster-RCNN network')
    # general
    parser.add_argument('--cfg', help='experiment configure file name', required=True, type=str)

    args, rest = parser.parse_known_args()
    # update config
    update_config(args.cfg)

    # training
    parser.add_argument('--frequent', help='frequency of logging', default=config.default.frequent, type=int)
    args = parser.parse_args()
    return args


args = parse_args()
curr_path = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(curr_path, '../external/mxnet', config.MXNET_VERSION))

import shutil
import mxnet as mx

from function.train_rcnn import train_rcnn
from utils.create_logger import create_logger


def main():
    print('Called with argument:', args)
    ctx = [mx.gpu(int(i)) for i in config.gpus.split(',')]
    logger, output_path = create_logger(config.output_path, args.cfg, config.dataset.image_set)
    shutil.copy2(os.path.join(curr_path, 'symbols', config.symbol + '.py'), output_path)

    assert config.TRAIN.END2END == False
    prefix = os.path.join(output_path, config.TRAIN.model_prefix)
    logging.info('########## TRAIN rcnn WITH IMAGENET INIT AND RPN DETECTION')
    train_rcnn(config, config.dataset.dataset, config.dataset.image_set, config.dataset.root_path,
               config.dataset.dataset_path,
               args.frequent, config.default.kvstore, config.TRAIN.FLIP, config.TRAIN.SHUFFLE, config.TRAIN.RESUME,
               ctx, config.network.pretrained, config.network.pretrained_epoch, prefix, config.TRAIN.begin_epoch,
               config.TRAIN.end_epoch, train_shared=False, lr=config.TRAIN.lr, lr_step=config.TRAIN.lr_step,
               proposal=config.dataset.proposal, logger=logger, output_path=output_path)


if __name__ == '__main__':
    main()
