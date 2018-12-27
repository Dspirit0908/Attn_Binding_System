# coding: utf-8

import sys
import torch
import logging
from utils import sequence_mask
from torch.distributions import Categorical

logger = logging.getLogger('binding')


class Policy:
    def __init__(self, args):
        self.args = args

    def select_action(self, probs, lengths, sql_labels):
        batch_size = probs.size(0)
        # notice the max_len
        max_len = probs.size(1)
        actions, log_probs = torch.LongTensor(batch_size, max_len).to(device=self.args.device), torch.FloatTensor(batch_size, max_len).to(device=self.args.device)
        probs = probs.transpose(0, 1).contiguous()
        for ti in range(max_len):
            actions[:, ti], log_probs[:, ti] = self.select_action_step(probs[ti])
        # mask
        mask = sequence_mask(lengths, max_len).to(device=self.args.device)
        actions.data.masked_fill_(1 - mask, -100)
        log_probs.data.masked_fill_(1 - mask, 0.0)
        # compute rewards
        rewards = self.compute_rewards(actions, sql_labels, mode='rewards')
        return torch.sum(log_probs, dim=1), rewards

    # todo: sample m actions
    def select_m_actions(self, probs, lengths, sql_labels):
        batch_size = probs.size(0)
        # notice the max_len
        max_len = probs.size(1)
        actions, log_probs = torch.LongTensor(batch_size, max_len).to(device=self.args.device), torch.FloatTensor(batch_size, max_len).to(device=self.args.device)
        probs = probs.transpose(0, 1).contiguous()
        for ti in range(max_len):
            actions[:, ti], log_probs[:, ti] = self.select_action_step(probs[ti])
        # mask
        mask = sequence_mask(lengths, max_len).to(device=self.args.device)
        actions.data.masked_fill_(1 - mask, -100)
        log_probs.data.masked_fill_(1 - mask, 0.0)
        # compute rewards
        rewards = self.compute_rewards(actions, sql_labels, mode='rewards')
        return torch.sum(log_probs, dim=1), rewards

    def select_action_step(self, probs_step):
        m = Categorical(probs_step)
        action = m.sample()
        return action, m.log_prob(action)

    # select max action, for test
    def select_max_action(self, probs, lengths, sql_labels):
        batch_size, max_len = probs.size(0), probs.size(1)
        actions = torch.max(probs, 2)[1]
        # mask
        mask = sequence_mask(lengths, max_len).to(device=self.args.device)
        actions.data.masked_fill_(1 - mask, -100)
        # compute acc
        rewards = self.compute_rewards(actions, sql_labels, mode='acc')
        return actions, rewards

    def compute_rewards(self, actions, sql_labels, mode='rewards'):
        batch_size = actions.size(0)
        rewards = torch.FloatTensor(batch_size).to(device=self.args.device)
        batch_sel_col, batch_conds_cols, batch_conds_values = sql_labels
        for bi in range(batch_size):
            pred, sel_col, conds_cols, conds_values = actions[bi], batch_sel_col[bi], batch_conds_cols[bi], batch_conds_values[bi]
            if mode == 'rewards':
                rewards[bi] = self.compute_rewards_step(pred, sel_col, conds_cols, conds_values)
            elif mode == 'acc':
                rewards[bi] = self.compute_acc_step(pred, sel_col, conds_cols, conds_values)
        return rewards

    def compute_rewards_step(self, action, sel_col, conds_cols, conds_values):
        action_cols = [tag - self.args.tokenize_max_len for tag in action.data.cpu().numpy() if tag >= self.args.tokenize_max_len and tag < self.args.tokenize_max_len + self.args.columns_split_marker_max_len - 1]
        action_vals = [index for index, tag in enumerate(action.data.cpu().numpy()) if tag >= self.args.tokenize_max_len + self.args.columns_split_marker_max_len - 1]
        sql_values = []
        for value in conds_values.data.cpu().numpy():
            if value[0] != -100:
                for index in range(value[0], value[1]):
                    sql_values.append(index)
        # three rules
        reward = -1.0
        sql_sel_col = int(sel_col.data.cpu().numpy())
        action_conds_cols = set(action_cols)
        if sql_sel_col in action_conds_cols:
            # need remove sel_col
            action_conds_cols.remove(sql_sel_col)
            # set(conds_cols.data.cpu().numpy()) include -100, but no affect for the result of issubset
            if action_conds_cols.issubset(set(conds_cols.data.cpu().numpy())):
                if action_vals == sql_values:
                    reward = 1.0
        return reward
    
    # reward 1 or 0, for test to compute acc
    def compute_acc_step(self, action, sel_col, conds_cols, conds_values):
        action_cols = [tag - self.args.tokenize_max_len for tag in action.data.cpu().numpy() if tag >= self.args.tokenize_max_len and tag < self.args.tokenize_max_len + self.args.columns_split_marker_max_len - 1]
        action_vals = [index for index, tag in enumerate(action.data.cpu().numpy()) if tag >= self.args.tokenize_max_len + self.args.columns_split_marker_max_len - 1]
        sql_values = []
        for value in conds_values.data.cpu().numpy():
            if value[0] != -100:
                for index in range(value[0], value[1]):
                    sql_values.append(index)
        # three rules
        reward = 0
        sql_sel_col = int(sel_col.data.cpu().numpy())
        action_conds_cols = set(action_cols)
        if sql_sel_col in action_conds_cols:
            action_conds_cols.remove(sql_sel_col)
            if action_conds_cols.issubset(set(conds_cols.data.cpu().numpy())):
                if action_vals == sql_values:
                    reward = 1.0
        # print(action)
        # print(action_cols, sel_col, conds_cols)
        # print(action_vals, sql_values)
        # print(reward)
        # print('######')
        return reward


if __name__ == '__main__':
    probs = torch.Tensor([[0.2, 0.5, 0.3], [0.7, 0.1, 0.2]])
    print(torch.sum(probs, dim=1))
