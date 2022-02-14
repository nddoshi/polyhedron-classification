import ipdb
import numpy as np
import math
import random
import scipy as scp
import torch
from torchvision import transforms


def default_transforms():
    return transforms.Compose([
        Normalize(),
    ])


def train_transforms(noise_scale=0.02):
    return transforms.Compose([
        Normalize(),
        RandRotation_z(),
        RandomNoise(scale=noise_scale),
    ])


def train_transforms_3DRot(noise_scale=0.02):
    return transforms.Compose([
        Normalize(),
        RandRotation_S03(),
        RandomNoise(scale=noise_scale),
    ])


class Normalize(object):
    def __call__(self, pointcloud):
        assert len(pointcloud.shape) == 2

        norm_pointcloud = pointcloud - np.mean(pointcloud, axis=0)
        norm_pointcloud /= np.max(np.linalg.norm(norm_pointcloud, axis=1))

        return norm_pointcloud


class RandRotation_z(object):
    def __call__(self, pointcloud):
        assert len(pointcloud.shape) == 2

        theta = random.random() * 2. * math.pi
        rot_matrix = np.array([[math.cos(theta), -math.sin(theta),    0],
                               [math.sin(theta),  math.cos(theta),    0],
                               [0,                             0,      1]])

        rot_pointcloud = rot_matrix.dot(pointcloud.T).T
        return rot_pointcloud


class RandRotation_S03(object):

    def __call__(self, pointcloud):

        assert len(pointcloud.shape) == 2

        R = scp.spatial.transform.Rotation.random().as_matrix()
        return R.dot(pointcloud.T).T


class RandomNoise(object):
    def __init__(self, scale=0.02):
        self.scale = scale

    def __call__(self, pointcloud):
        assert len(pointcloud.shape) == 2

        noise = np.random.normal(0, self.scale, (pointcloud.shape))

        noisy_pointcloud = pointcloud + noise
        return noisy_pointcloud
