# coding: utf-8

import os
import json
import torch
import logging
import functools
from config import Args
from train import train, eval, train_rl, eval_rl, test
from models.gate import Gate
from models.bert_gate import BertGate
from models.baseline import Baseline
from dataloader import BindingDataset
from torch.utils.data import Dataset, DataLoader
from utils import UNK_WORD, BOS_WORD, build_all_vocab, set_seed, load_word_embedding, add_abstraction, anonymous


def main(mode, args):
    # build vocab
    word2index, index2word = build_all_vocab(init_vocab={UNK_WORD: 0, BOS_WORD: 1})
    args.vocab, args.vocab_size, args.index2word = word2index, len(word2index), index2word
    # get data_from_train from only_label = True, for same as train baseline
    args.only_label = True
    train_dataset = BindingDataset('train', args=args)
    data_from_train = (train_dataset.tokenize_max_len, train_dataset.columns_token_max_len,
                       train_dataset.columns_split_marker_max_len, train_dataset.cells_token_max_len,
                       train_dataset.cells_split_marker_max_len, train_dataset.pos_tag_vocab,
                       train_dataset.bert_tokenize_max_len, train_dataset.bert_tokenize_marker_max_len,
                       train_dataset.bert_columns_split_max_len, train_dataset.bert_columns_split_marker_max_len,
                       train_dataset.bert_cells_split_max_len, train_dataset.bert_cells_split_marker_max_len)
    args.tokenize_max_len, args.columns_token_max_len, args.columns_split_marker_max_len, \
    args.cells_token_max_len, args.cells_split_marker_max_len, args.pos_tag_vocab,\
    args.bert_tokenize_max_len, args.bert_tokenize_marker_max_len, args.bert_columns_split_max_len, args.bert_columns_split_marker_max_len,\
    args.bert_cells_split_max_len, args.bert_cells_split_marker_max_len = data_from_train
    logger.info('data_from_train'), logger.info(data_from_train)
    # set only_label
    if mode == 'train baseline':
        args.only_label = True
    elif mode == 'policy gradient':
        args.only_label = False
    elif mode == 'test model':
        args.only_label = True
    elif mode == 'add feature':
        args.only_label = False
    elif mode == 'write cases':
        args.only_label = True
    elif mode == 'anonymous':
        args.only_label = False
    # build train_dataloader
    train_dataset = BindingDataset('train', args=args, data_from_train=data_from_train)
    train_dataloader = DataLoader(dataset=train_dataset, batch_size=args.batch_size, shuffle=args.shuffle)
    # build dev_dataloader
    args.shuffle = False
    dev_dataset = BindingDataset('dev', args=args, data_from_train=data_from_train)
    dev_dataloader = DataLoader(dataset=dev_dataset, batch_size=args.batch_size, shuffle=args.shuffle)
    # build test_dataloader
    # test_dataset = BindingDataset('test', args=args, data_from_train=data_from_train)
    # test_dataloader = DataLoader(dataset=test_dataset, batch_size=args.batch_size, shuffle=args.shuffle)
    # load word embedding
    if args.load_w2v:
        args.embed_matrix = load_word_embedding(args.word_dim, word2index)
    # train
    if mode == 'train baseline':
        if args.model == 'baseline':
            model = Baseline(args=args)
        elif args.model == 'gate':
            if args.bert_model is None:
                model = Gate(args=args)
            else:
                model = BertGate(args=args)
        else:
            raise NotImplementedError
        train(train_dataloader, dev_dataloader, args=args, model=model)
    elif mode == 'policy gradient':
        model = torch.load('./res/' + args.model + '/2816_False_True_True_726425', map_location=lambda storage, loc: storage.cuda(0))
        train_rl(train_dataloader, dev_dataloader, args=args, model=model)
    elif mode == 'test model':
        # also need the correct 'model' for dataloader
        model = torch.load('./res/policy_gradient/0.819928_True_True_True_412532', map_location=lambda storage, loc: storage.cuda(0))
        eval(dev_dataloader, args, model, epoch=0)
        eval_rl(dev_dataloader, args, model, epoch=0)
    elif mode == 'add feature':
        model = torch.load('./res/policy_gradient/0.804922_22-16-28', map_location=lambda storage, loc: storage.cuda(0))
        res = test(dev_dataloader, args, model)
        add_abstraction('dev', res=res, args=args)
    elif mode == 'write cases':
        model = torch.load('./res/policy_gradient/0.819928_True_True_True_412532', map_location=lambda storage, loc: storage.cuda(0))
        res_pg = test(dev_dataloader, args, model, sep=' ')
        model = torch.load('./res/gate/epoch100', map_location=lambda storage, loc: storage.cuda(0))
        res_gate = test(dev_dataloader, args, model, sep=' ')
        with open('cases.txt', 'w', encoding='utf-8') as f:
            for key in res_pg.keys():
                # diff between gate and policy
                if res_gate[key]['pred'] != res_pg[key]['pred']:
                    if res_gate[key]['pred'] == res_gate[key]['label']:
                        f.write(key + '\n')
                        f.write('Pred_Gate:\t\t\t\t' + json.dumps(res_gate[key]['pred']) + '\n')
                        f.write('Pred_Policy_Gradient:\t' + json.dumps(res_pg[key]['pred']) + '\n')
                        f.write('Label:\t\t\t\t\t' + json.dumps(res_pg[key]['label']) + '\n')
                        f.write('SQL_Labels:\t\t\t\t' + json.dumps(res_pg[key]['sql_labels']) + '\n' + '\n')
    elif mode == 'anonymous':
        model = torch.load('./res/policy_gradient/0.819928_True_True_True_412532', map_location=lambda storage, loc: storage.cuda(0))
        res = test(train_dataloader, args, model, sep='')
        anonymous('train', res, args)


if __name__ == '__main__':
    # set environ, loggging
    print(torch.cuda.device_count())
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger('binding')
    # set args
    args = Args()
    set_seed(args.seed)
    logger.info(args.device)
    # set model
    args.model = 'gate'
    # args.load_w2v, args.word_dim = True, 300
    args.cell_info = False
    args.attn_concat = True
    args.crf = False
    # args.bert_model = None
    main('train baseline', args)
    # main('test model', args)
    # main('policy gradient', args)
    # main('add feature', args)
    # main('write cases', args)
    # main('anonymous', args)
