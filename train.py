import ipdb
import numpy as np
import random
import os
import torch
from torch.utils.data import DataLoader

from source import model
from source import polyhedron_dataset
from source import polyhedron_utils
from source import train_utils
from source import save_utils
from source.args import parse_train_args
from source.visualization import TensorBoardVis


if __name__ == '__main__':

    # arguments
    args = parse_train_args()

    # set random seed
    torch.manual_seed(args.random_seed)
    random.seed(args.random_seed)
    np.random.seed(args.random_seed)

    # setup experiment
    exp_save_dir, tb_save_dir = save_utils.save_experiment(args=args)
    if args.save_flag:
        print("Saving experiment...")

    # device
    device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
    print(f"Using {device} for training")

    # training dataset
    train_ds = polyhedron_dataset.PolyhedronDataSet(
        pc_type=args.point_cloud_type,
        data_dir=os.path.join(args.dataset_dir, 'train'),
        transform=polyhedron_utils.train_transforms_3DRot,
        noise_scale=0.02)

    train_loader = DataLoader(
        dataset=train_ds, batch_size=args.batch_size,
        collate_fn=train_ds.collate_fn, shuffle=True)

    # testing dataset
    valid_ds = polyhedron_dataset.PolyhedronDataSet(
        pc_type=args.point_cloud_type,
        data_dir=os.path.join(args.dataset_dir, 'test'),
        transform=polyhedron_utils.default_transforms,
        noise_scale=0.02)

    valid_loader = DataLoader(
        dataset=valid_ds, batch_size=len(valid_ds),
        collate_fn=valid_ds.collate_fn, shuffle=True)

    # print dateset info
    num_classes = len(np.unique(np.array(train_ds.labels)))
    print(f'Train dataset size: {len(train_ds)}')
    print(f'Valid dataset size: {len(valid_ds)}')
    print(f'Number of classes: {num_classes}')

    # model
    pointnet = model.PointNet(classes=num_classes, p_dropout=args.p_dropout)
    pointnet.to(device)

    # optimizer
    optimizer = torch.optim.Adam(pointnet.parameters(), lr=args.lr,
                                 weight_decay=args.weight_decay)
    lossfn = train_utils.pointnetloss

    if args.resume_epoch > 0:
        checkpoint_path, _ = save_utils.load_experiment(
            args=args)
        checkpoint = torch.load(checkpoint_path, map_location=device)
        pointnet.load_state_dict(checkpoint['model_state_dict'])
        optimizer.load_state_dict(checkpoint['opt_state_dict'])

    # tensorboard visualization
    tensorboard_vis = TensorBoardVis(log_dir=tb_save_dir, device=device)

    step = 0
    train_utils.test_loop(
        dataloader=valid_loader, train_dataset=train_ds,
        model=pointnet, lossfn=lossfn, device=device,
        tensorboard_vis=tensorboard_vis, step=step)

    for epoch in range(args.epochs):
        print(f"Epoch {epoch+1}\n-------------------------------")

        tb_log_flag = ((epoch+1) % args.tb_log_freq == 0)

        train_loss, train_accuracy, save_data, step = train_utils.train_loop(
            dataloader=train_loader, model=pointnet, lossfn=lossfn,
            optimizer=optimizer, device=device,
            tensorboard_vis=tensorboard_vis if tb_log_flag else None,
            step=step, debug=args.debug)

        test_loss, test_accuracy, _, _, _, _ = train_utils.test_loop(
            dataloader=valid_loader, train_dataset=train_ds,
            model=pointnet, lossfn=lossfn, device=device,
            tensorboard_vis=tensorboard_vis if tb_log_flag else None,
            step=step)

        # save the model
        if args.save_flag and ((epoch+1) % args.save_freq == 0):
            save_utils.save_checkpoint(
                save_dir=exp_save_dir,
                epoch=epoch,
                model=pointnet,
                optimizer=optimizer,
                data=save_data,
                stats={'train_loss': train_loss,
                       'train_accuracy': train_accuracy,
                       'test_loss': test_loss,
                       'test_accuracy': test_accuracy}
            )

    if tensorboard_vis:
        tensorboard_vis.close_writer()
    print("Done!")
