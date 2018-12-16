# coding: utf-8

import torch

data_path = './data/'
wikisql_path = data_path + 'wikisql/'
preprocess_path = data_path + 'preprocess/'
label_path = data_path + 'label/'


# hyperparameters
class Args(object):
    def __init__(self):
        self.seed = 1
        self.lr = 0.001
        self.weight_decay = 0.002
        self.epochs = 50
        self.batch_size = 512
        self.log_trian_interval = 25
        self.log_test_interval = 2
        self.dropout_p = 0.1
        self.load_w2v = False
        self.shuffle = False
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.cuda = True if str(self.device) == 'cuda' else False
        self.word_dim = 100
        self.hidden_size = 32
        self.num_layers = 1
        self.teacher_forcing_ratio = 0.5


if __name__ == '__main__':
    args = Args()
    print(args.cuda)
