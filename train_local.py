
import sys
import time
from options.train_options import TrainOptions
from data import create_dataset
from models import create_model
from util.visualizer import Visualizer
import os
import gc
import torch
import numpy as np
from matplotlib import pyplot as plt
import re

os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'

def main():
    opt = TrainOptions().parse()

    gtest_dataset = create_dataset(opt, 'global', opt.ctest_batch_size)
    ctrain_dataset = create_dataset(opt, 'train', opt.ctrain_batch_size)
    ctest_dataset = create_dataset(opt, 'test', opt.ctest_batch_size)

    dataset_size = len(ctrain_dataset)
    print('The number of training images = %d' % dataset_size)
    save_dir = os.path.join(opt.checkpoints_dir, opt.name)
    g_acc = []
    g_loss = []
    c_acc = [0 for _ in range(opt.n_client)]
    c_loss = [0 for _ in range(opt.n_client)]

    for k in range(opt.n_fold):
        print(f'run in {k} fold:')

        model = create_model(opt)
        model.setup(opt)
        total_iters = 0

        for epoch in range(opt.epoch_count, opt.rounds + 1):
            print('>> train C in ({})/({})'.format(epoch, opt.rounds + 1))
            epoch_iter = 0
            for i, data in enumerate(ctrain_dataset):
                model.set_input(data)
                model.train_C(epoch)

            closs, c_correct, c_num_all_samples = model.test_C(ctest_dataset, k)

            if epoch == opt.rounds:
                for i in range(opt.n_client):
                    c_acc[i] += (100. * c_correct[i] / c_num_all_samples[i]).cpu().numpy().tolist()
                    c_loss[i] += closs[i]
        loss, correct, num_all_samples, acc = model.test_and_save(gtest_dataset, k, 'global')
        g_acc.append(acc.cpu().numpy().tolist())
        g_loss.append(loss)
        gc.collect()
        torch.cuda.empty_cache()

    print(f'total result acc:{np.mean(g_acc)}, loss:{np.mean(g_loss)}')

    file = save_dir + '/result.txt'
    with open(file, 'a') as f:
        f.write(f'global total result acc:{np.mean(g_acc)}, loss:{np.mean(g_loss)}\n')
        for i in range(opt.n_client):
            f.write(f'client {i} local result acc:{c_acc[i] / opt.n_fold}, loss:{c_loss[i] / opt.n_fold}\n')
        f.close()

if __name__ == '__main__':
    main()
