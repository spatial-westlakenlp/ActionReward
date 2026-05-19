import numpy as np
from pathlib import Path
import json
from collections import defaultdict
from sklearn.metrics import roc_auc_score, precision_recall_curve, auc
from scipy.stats import ks_2samp, mannwhitneyu
from scipy.stats import spearmanr, kendalltau
from pprint import pprint
        
def evaluate_system(np_scores_dict, y_true):
    results = {}
    for score_name in np_scores_dict: 
        scores = np_scores_dict[score_name]

        pos_scores = scores[y_true == 1]
        neg_scores = scores[y_true == 0]

        auc_roc = roc_auc_score(y_true, scores)

        precision, recall, _ = precision_recall_curve(y_true, scores)
        aupr = auc(recall, precision)

        ks = ks_2samp(pos_scores, neg_scores).statistic 
        
        u_stat, p_value = mannwhitneyu(pos_scores, neg_scores, alternative="greater")

        spearman_corr, spearman_p = spearmanr(y_true, scores)
        kendall_corr, kendall_p = kendalltau(y_true, scores)
        
        results[score_name] = {
            "AUC-ROC": round(auc_roc, 3),
            "AUPR": round(aupr, 3),
            "KS": round(ks, 3),
            "Spearman Corr": round(spearman_corr, 3),
            "Kendall Corr": round(kendall_corr, 3),
            "p_value": round(p_value, 30)
        }
    return results


if __name__=="__main__":
    score_fns = [
        './storage/eval_scores/mdm.json',
        './storage/eval_scores/mgpt.json',
    ]
    reserved_fns = [
        './storage/reserved_ids.txt'
    ]

    reserved_ids = set([])
    for reserved_fn in reserved_fns:
        with Path(reserved_fn).open('r') as f:
            reserved_ids.update([e.strip() for e in f.readlines()])


    scores_dict = defaultdict(list)
    y_true = []
    for score_fn in score_fns:
        with Path(score_fn).open('r') as f:
            saved_scores = json.load(f)

        for data_id,record in saved_scores.items():
            if data_id not in reserved_ids:
                continue
            for score_name in record['score']:
                if record['score'][score_name] is None:
                    continue
                scores_dict[score_name].append(record['score'][score_name])
            y_true.append(record['oracle human label'])

    np_scores_dict = {}
    score_lens = []
    for score_name in scores_dict:
        np_scores_dict[score_name] = np.array(scores_dict[score_name])
        assert len(scores_dict[score_name]) == len(y_true)
    y_true = np.array(y_true)


    results = evaluate_system(np_scores_dict, y_true)
    pprint(results)
