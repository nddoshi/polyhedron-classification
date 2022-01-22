import ipdb
import numpy as np
import torch

from source import visualization


def pointnetloss(outputs, labels, m3x3, m64x64, alpha=0.0001):
    ''' loss function '''

    criterion = torch.nn.NLLLoss()  # negative log likelihood loss
    batch_size = outputs.size(0)
    id3x3 = torch.eye(3, requires_grad=True).repeat(batch_size, 1, 1)
    id64x64 = torch.eye(64, requires_grad=True).repeat(batch_size, 1, 1)
    if outputs.is_cuda:
        id3x3 = id3x3.cuda()
        id64x64 = id64x64.cuda()
    diff3x3 = id3x3-torch.bmm(m3x3, m3x3.transpose(1, 2))
    diff64x64 = id64x64-torch.bmm(m64x64, m64x64.transpose(1, 2))
    return criterion(outputs, labels) + alpha * (
        torch.norm(diff3x3)+torch.norm(diff64x64)) / float(batch_size)


def build_tensorboard_scalars(tags, scalars, steps):
    ''' build scalars for tensorboard'''

    assert len(tags) == len(scalars) and len(scalars) == len(steps)

    scalar_updates = []
    for tag, scalar, step in zip(tags, scalars, steps):
        scalar_updates.append({
            'tag': tag, 'scalar_value': scalar, 'global_step': step
        })

    return scalar_updates


def train_loop(dataloader, model, lossfn, optimizer, device,
               tensorboard_vis=None, step=0):

    total_loss, total_correct = 0, 0
    all_inputs, all_preds, all_labels = [], [], []

    for batch, (X, y) in enumerate(dataloader):

        # get data
        inputs, labels = X.to(device).float(), y.to(device)

        # current prediction and loss
        outputs, m3x3, m64x64 = model(inputs.transpose(1, 2))
        predicted_labels = outputs.argmax(1)
        loss = lossfn(outputs, labels, m3x3, m64x64)
        correct = (predicted_labels ==
                   labels).type(torch.float).sum().item()

        # backprop
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        # append
        if device.type == 'cpu':
            all_inputs.append(inputs.numpy())
            all_preds.extend(predicted_labels.tolist())
            all_labels.extend(labels.tolist())
        else:
            all_inputs.append(inputs.cpu().numpy())
            all_preds.extend(predicted_labels.tolist())
            all_labels.extend(labels.cpu().tolist())

        # print statistics
        loss = loss.item()
        accuracy = correct/len(labels)
        print(
            f"loss: {loss:>7f}, accuracy: {100*accuracy}%, [{(batch+1)*len(X):>5d}/{len(dataloader.dataset):>5d}]")

        # build tensorboard update
        if tensorboard_vis:
            scalar_update_list = build_tensorboard_scalars(
                tags=['Loss/train per step', 'Accuracy/train per step'],
                scalars=[loss, accuracy],
                steps=[step + batch + 1, step + batch + 1])

            tensorboard_vis.update_writer({'scalar': scalar_update_list})

        # cumulative statistics
        total_loss += loss
        total_correct += accuracy

    if tensorboard_vis:
        figure_update_list = [{
            'tag': 'Confusion Matrix/train per step',
            'figure': visualization.plot_confusion_matrix(
                dataset=dataloader.dataset, preds=all_preds,
                true_vals=all_labels),
            'global_step': step + batch + 1
        }]

        tensorboard_vis.update_writer({'figure': figure_update_list})

    return (total_loss/len(dataloader),
            total_correct/len(dataloader.dataset),
            step + batch + 1)


def test_loop(dataloader, train_dataset, model, lossfn, device,
              tensorboard_vis=None, step=0):

    total_loss, total_correct = 0, 0
    all_inputs, all_preds, all_labels = [], [], []
    with torch.no_grad():
        for X, y in dataloader:

            # get data
            inputs, labels = X.to(device).float(), y.to(device)

            # predictions
            outputs, m3x3, m64x64 = model(inputs.transpose(1, 2))
            predictions = outputs.argmax(1)

            # loss and accuracy
            total_loss += lossfn(outputs, labels, m3x3, m64x64).item()
            total_correct += (predictions ==
                              labels).type(torch.float).sum().item()

            # append
            if device.type == 'cpu':
                all_inputs.append(inputs.numpy())
                all_preds.extend(predictions.tolist())
                all_labels.extend(labels.tolist())
            else:
                all_inputs.append(inputs.cpu().numpy())
                all_preds.extend(predictions.cpu().tolist())
                all_labels.extend(labels.cpu().tolist())

    total_loss /= len(dataloader)
    total_correct /= len(dataloader.dataset)
    print(
        f"Test Error:  Accuracy: {(100*total_correct):>0.1f}%, Avg loss: {total_loss:>8f} \n")

    if tensorboard_vis:
        # build tensorboard update
        scalar_update_list = build_tensorboard_scalars(
            tags=['Loss/test per step', 'Accuracy/test per step'],
            scalars=[total_loss, total_correct],
            steps=[step, step])

        figure_update_list = [{
            'tag': 'Confusion Matrix/test per step',
            'figure': visualization.plot_confusion_matrix(
                dataset=train_dataset, preds=all_preds,
                true_vals=all_labels),
            'global_step': step
        }]

        # update tensorboard
        tensorboard_vis.update_writer({'scalar': scalar_update_list,
                                       'figure': figure_update_list})

    return (total_loss,
            total_correct,
            np.concatenate(all_inputs, axis=0),
            all_preds,
            all_labels)
