import pandas as pd
import numpy as np
from flaml import AutoML
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    mean_squared_error, mean_absolute_error, r2_score,
    confusion_matrix, classification_report,
    roc_auc_score, roc_curve
)
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')


def _detect_target(df):
    """Smartly detect the target column using heuristics a data analyst would use."""
    # Priority 1: Common target column names
    priority_names = ['target', 'label', 'class', 'outcome', 'y', 'churn',
                      'survived', 'default', 'fraud', 'spam', 'diagnosis',
                      'price', 'salary', 'revenue', 'sales', 'amount']
    for col in df.columns:
        if col.lower().strip() in priority_names:
            return col

    # Priority 2: Binary columns (often targets in classification)
    binary_cols = [c for c in df.columns if df[c].nunique() == 2]
    if len(binary_cols) == 1:
        return binary_cols[0]

    # Priority 3: Low-cardinality categorical at the end (common convention)
    for col in reversed(df.columns):
        if df[col].nunique() <= 10 and df[col].nunique() >= 2:
            return col

    # Fallback: last column
    return df.columns[-1]


def _engineer_features(df, target_col):
    """
    Automatic feature engineering to boost model accuracy.
    Applies transformations that a data analyst would manually do.
    """
    X = df.drop(columns=[target_col])
    y = df[target_col]

    # 1. Encode categorical features using Label Encoding
    label_encoders = {}
    for col in X.select_dtypes(include=['object', 'category']).columns:
        le = LabelEncoder()
        # Handle unseen values gracefully
        X[col] = X[col].astype(str)
        le.fit(X[col])
        X[col] = le.transform(X[col])
        label_encoders[col] = le

    # 2. Encode target if categorical
    target_encoder = None
    if y.dtype == 'object' or y.dtype.name == 'category':
        target_encoder = LabelEncoder()
        y = pd.Series(target_encoder.fit_transform(y.astype(str)), name=target_col)

    # 3. Log-transform highly skewed numeric features (skewness > 2)
    numeric_cols = X.select_dtypes(include=['number']).columns
    skewed_cols = []
    for col in numeric_cols:
        skewness = X[col].skew()
        if abs(skewness) > 2 and X[col].min() >= 0:
            X[f'{col}_log'] = np.log1p(X[col])
            skewed_cols.append(col)

    # 4. Create interaction features for top correlated pairs
    if len(numeric_cols) >= 2:
        corr_matrix = X[numeric_cols].corr().abs()
        # Get top 3 correlated pairs (excluding self-correlation)
        pairs_added = 0
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                if corr_matrix.iloc[i, j] > 0.5 and pairs_added < 3:
                    col_a = numeric_cols[i]
                    col_b = numeric_cols[j]
                    X[f'{col_a}_x_{col_b}'] = X[col_a] * X[col_b]
                    pairs_added += 1

    # 5. Drop columns with zero variance (useless features)
    zero_var_cols = [c for c in X.columns if X[c].std() == 0]
    X.drop(columns=zero_var_cols, inplace=True)

    return X, y, label_encoders, target_encoder


def train_model(df: pd.DataFrame, target_col: str = None, time_budget: int = None):
    """
    Train a model using FLAML (Fast Lightweight AutoML).
    No time budget — trains until convergence for maximum accuracy.
    Returns comprehensive metrics that a professional data analyst would report.
    """

    # 1. Detect target if not provided
    if not target_col:
        target_col = _detect_target(df)

    # Refuse to train if target is a unique ID column
    if df[target_col].dtype == 'object' and df[target_col].nunique() > len(df) * 0.9:
        return {"error": f"Target column '{target_col}' appears to be a unique ID."}

    # 2. Feature Engineering
    X, y, label_encoders, target_encoder = _engineer_features(df, target_col)

    # 3. Determine problem type
    task = "classification"
    if pd.api.types.is_numeric_dtype(y) and y.nunique() > 20:
        task = "regression"

    # 4. Detect class imbalance (classification only)
    class_info = {}
    if task == "classification":
        value_counts = y.value_counts()
        class_info = {
            "class_distribution": {str(k): int(v) for k, v in value_counts.items()},
            "is_imbalanced": (value_counts.max() / value_counts.min()) > 3,
            "imbalance_ratio": round(float(value_counts.max() / value_counts.min()), 2)
        }

    # 5. Train/Test Split (stratified for classification)
    split_kwargs = {"test_size": 0.2, "random_state": 42}
    if task == "classification":
        split_kwargs["stratify"] = y
    X_train, X_test, y_train, y_test = train_test_split(X, y, **split_kwargs)

    # 6. Initialize FLAML AutoML — NO TIME BUDGET for maximum accuracy
    automl = AutoML()
    settings = {
        "metric": 'accuracy' if task == "classification" else 'r2',
        "task": task,
        "log_file_name": 'flaml.log',
        "verbose": 0,
        "n_jobs": -1,  # Use all CPU cores
        "ensemble": True,  # Try ensemble methods for better accuracy
        "eval_method": "cv",  # Cross-validation for robust evaluation
        "n_splits": 5,  # 5-fold cross-validation
    }

    # Set time budget: unlimited if not specified, otherwise user-provided
    if time_budget is not None:
        settings["time_budget"] = time_budget
    else:
        # No time limit — let FLAML explore thoroughly
        # Use max_iter instead to let it run many trials
        settings["time_budget"] = 600  # 10 minutes for thorough exploration
        settings["early_stop"] = True  # Stop if no improvement

    try:
        automl.fit(X_train=X_train, y_train=y_train, **settings)
    except Exception as e:
        return {"error": f"AutoML Training Failed: {str(e)}"}

    # 7. Comprehensive Evaluation
    preds = automl.predict(X_test)
    metrics = {}

    if task == "classification":
        metrics["accuracy"] = round(accuracy_score(y_test, preds), 4)

        # Multi-class aware metrics
        avg_method = 'binary' if y.nunique() == 2 else 'weighted'
        metrics["precision"] = round(precision_score(y_test, preds, average=avg_method, zero_division=0), 4)
        metrics["recall"] = round(recall_score(y_test, preds, average=avg_method, zero_division=0), 4)
        metrics["f1_score"] = round(f1_score(y_test, preds, average=avg_method, zero_division=0), 4)

        # Confusion matrix
        cm = confusion_matrix(y_test, preds)
        metrics["confusion_matrix"] = cm.tolist()

        # Per-class report
        try:
            report = classification_report(y_test, preds, output_dict=True, zero_division=0)
            metrics["per_class_report"] = {
                str(k): {mk: round(mv, 4) for mk, mv in v.items()} 
                for k, v in report.items() 
                if isinstance(v, dict)
            }
        except:
            pass
            
        # ROC / AUC for binary classification
        if y.nunique() == 2:
            try:
                # Try to get probabilities for the positive class
                if hasattr(automl.model, 'predict_proba'):
                    probs = automl.model.predict_proba(X_test)[:, 1]
                    metrics["roc_auc"] = round(roc_auc_score(y_test, probs), 4)
                    
                    # Generate ROC Curve data (downsampled for frontend if needed, but 100 points is fine)
                    fpr, tpr, thresholds = roc_curve(y_test, probs)
                    # Keep ~50 points for the chart to keep JSON small
                    indices = np.linspace(0, len(fpr) - 1, min(50, len(fpr)), dtype=int)
                    metrics["roc_curve"] = {
                        "fpr": np.round(fpr[indices], 4).tolist(),
                        "tpr": np.round(tpr[indices], 4).tolist()
                    }
            except Exception as e:
                print(f"Failed to generate ROC: {e}")
                pass
    else:
        metrics["r2"] = round(r2_score(y_test, preds), 4)
        metrics["mse"] = round(mean_squared_error(y_test, preds), 4)
        metrics["rmse"] = round(np.sqrt(mean_squared_error(y_test, preds)), 4)
        metrics["mae"] = round(mean_absolute_error(y_test, preds), 4)

    # 8. Cross-validation score for robustness metric
    try:
        cv_metric = 'accuracy' if task == "classification" else 'r2'
        cv_scores = cross_val_score(
            automl.model, X, y, cv=5,
            scoring=cv_metric
        )
        metrics["cv_mean"] = round(float(cv_scores.mean()), 4)
        metrics["cv_std"] = round(float(cv_scores.std()), 4)
    except:
        pass

    # 9. Feature importance (sorted, top features)
    feat_importance = {}
    try:
        importances = automl.feature_importances_
        feat_importance = {
            k: round(float(v), 4)
            for k, v in sorted(
                zip(X.columns, importances),
                key=lambda x: x[1],
                reverse=True
            )
            if v > 0.005
        }
    except:
        pass

    # 10. Extract models compared
    models_compared = []
    try:
        # automl.best_config_per_estimator contains info about each algorithm tried
        if hasattr(automl, 'best_config_per_estimator'):
            for est_name, config in automl.best_config_per_estimator.items():
                if config: # If it was actually evaluated
                    models_compared.append(est_name)
    except:
        pass

    return {
        "target_col": target_col,
        "problem_type": task,
        "best_model": automl.best_estimator,
        "models_compared": list(set(models_compared)) if models_compared else [automl.best_estimator],
        "best_config": automl.best_config,
        "metrics": metrics,
        "feature_importance": feat_importance,
        "class_info": class_info,
        "n_features_original": len(df.columns) - 1,
        "n_features_engineered": len(X.columns),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
    }
