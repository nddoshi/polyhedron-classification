
import ipdb
import numpy as np
import os
import pickle
import plotly.subplots
import plotly.graph_objects as pgo
from torch.utils.data import Dataset

import source.polyhedron_utils
# import polyhedron_utils


class PolyhedronDataSet(Dataset):

    def __init__(self, pc_type, data_dir, transform=None):

        self.data_dir = data_dir
        self.transform = transform

        self.data = []
        self.nfaces = []

        for dir in sorted(os.listdir(self.data_dir)):
            dir_path = os.path.join(data_dir, dir)
            if os.path.isdir(dir_path):

                # all info files
                info_files = sorted([file for file in os.listdir(dir_path) if
                                     os.path.splitext(file)[1] == '.pickle'])

                # get polygon label
                for file in info_files:

                    with open(os.path.join(dir_path, file), 'rb') as handle:
                        polyhedron_info = pickle.load(handle)

                    polyhedron_dir_path = os.path.join(self.data_dir,
                                                       os.path.splitext(file)[0])

                    self.nfaces.append(polyhedron_info['n_faces'])

                    if pc_type == 'drake_point_cloud':
                        drake_pc_path = os.path.join(polyhedron_dir_path,
                                                     os.path.splitext(file)[0] + '_drake_pc.npy')
                        self.data.append(drake_pc_path)
                    elif pc_type == 'ideal_point_cloud':
                        ideal_pc_path = os.path.join(polyhedron_dir_path,
                                                     os.path.splitext(file)[0] + '_pc.npy')
                        self.data.append(ideal_pc_path)
                    else:
                        raise RuntimeError("incorrect point cloud type")

        ct, self.class_dict, self.label_dict = 0, {}, {}
        for nface in sorted(self.nfaces):
            if not nface in self.class_dict:
                self.class_dict[nface] = ct
                self.label_dict[ct] = nface
                ct += 1

        self.labels = [self.class_dict[nface] for nface in self.nfaces]

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, idx):

        pointcloud = np.load(self.data[idx])
        label = self.labels[idx]

        if self.transform:
            pointcloud = self.transform(pointcloud)

        return pointcloud, label

    def get_nsides_from_labels(self, labels):
        ''' get number of sides from polygon labels'''
        return [self.label_dict[label] for label in labels]

    def plot_sample(self, idx):
        ''' plot sample'''
        # print(self.data[idx])

        pointcloud = np.load(self.data[idx])

        if self.transform:
            pointcloud = self.transform(pointcloud)

        # plot sampled points
        data = pgo.Scatter3d(x=pointcloud[:, 0],
                             y=pointcloud[:, 1],
                             z=pointcloud[:, 2],
                             mode='markers',
                             marker_size=1,
                             marker_symbol='circle',
                             marker_color='rgba(0, 0, 255, 1)')

        return data

    def plot_pointclouds(self, pointclouds):
        ''' plot a point cloud'''

        pointclouds = pointclouds.numpy()

        for pointcloud in pointclouds:
            data = pgo.Scatter3d(x=pointcloud[0, :],
                                 y=pointcloud[1, :],
                                 z=pointcloud[2, :],
                                 mode='markers',
                                 marker_size=1,
                                 marker_symbol='circle',
                                 marker_color='rgba(0, 0, 255, 1)')
            fig = pgo.Figure(data)
            fig.show()


# if __name__ == "__main__":

#     pc_type = 'ideal_point_cloud'
#     data_dir = '/home/nddoshi/Research/learning_sandbox/datasets/Polygon'

#     dataset = PolyhedronDataSet(
#         pc_type=pc_type, data_dir=data_dir,
#         transform=polyhedron_utils.train_transforms(scale=0.02))

#     sample_ind = np.random.randint(0, dataset.__len__()-1)
#     sample = dataset.__getitem__(sample_ind)
#     print(sample['class'])
#     print(os.path.splitext(dataset.data[sample_ind])[0] + '.html')
#     label = dataset.labels[sample_ind]
#     nface = dataset.nfaces[sample_ind]
#     ncols = 2
#     fig = plotly.subplots.make_subplots(rows=2, cols=ncols,
#                                         specs=[[{"type": "scene"}] * ncols]*2,
#                                         subplot_titles=[f"Class: {label}, Sides: {nface}"]*2*ncols)

#     for i in range(2 * ncols):
#         plot_data = dataset.plot_sample(sample_ind)
#         fig.add_trace(plot_data, row=i//ncols + 1, col=i % ncols + 1)

#     print(dataset.class_dict)
#     fig.show()
