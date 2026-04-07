import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
from sklearn.model_selection import train_test_split, TimeSeriesSplit, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.linear_model import LinearRegression
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor
from xgboost import XGBRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Set plot style
plt.style.use('ggplot')
sns.set_palette('viridis')

# 1. Load Dataset
print("--- Step 1: Loading Dataset ---")
df = pd.read_csv("EV_Charging_Load_Demand_Dataset.csv")

# 2. Data Cleaning & Feature Selection
print("--- Step 2: Cleaning and Feature Selection ---")
# Drop leakage columns 
leakage_cols = ['station_load_kW'] 
df = df.drop(columns=[c for c in leakage_cols if c in df.columns], errors='ignore')

# Drop noisy high-cardinality columns (Aligned with ML_Models.ipynb)
# These columns are specific IDs/Locations that don't generalize well for system-wide prediction
noise_cols = ['vehicle_id', 'lane_id', 'current_station_id']
df = df.drop(columns=[c for c in noise_cols if c in df.columns], errors='ignore')

# Categorical Encoding
categorical_cols = ['status'] # vehicle_id, lane_id, current_station_id were dropped as noise
le = LabelEncoder()
for col in categorical_cols:
    if col in df.columns:
        df[col] = le.fit_transform(df[col].astype(str))

# Define Features and Target
X = df.drop(columns=['system_total_load_kW'])
y = df['system_total_load_kW']

# 3. Random Shuffled Splitting [ORIGINAL METHODOLOGY]
print("--- Step 3: Random Shuffled Splitting ---")
# Reverting to shuffled split as per ML_Models.ipynb to capture full range of load states
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

print(f"Training samples: {len(X_train)} | Testing samples: {len(X_test)}")

# 4. Multi-Model Training [CORE]
print("--- Step 4: Training Models ---")
# Exact Hyperparameters from ML_Models.ipynb
models = {
    "Linear Regression": LinearRegression(),
    "Decision Tree": DecisionTreeRegressor(max_depth=10, random_state=42),
    "Random Forest": RandomForestRegressor(n_estimators=100, max_depth=15, random_state=42),
    "XGBoost": XGBRegressor(n_estimators=200, learning_rate=0.1, max_depth=6, random_state=42)
}

results = []
trained_models = {}

for name, model in models.items():
    print(f"Training {name}...")
    # Scale for Linear Regression
    if name == "Linear Regression":
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        model.fit(X_train_scaled, y_train)
        preds = model.predict(X_test_scaled)
    else:
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
    
    trained_models[name] = model
    
    # Calculate Metrics
    mae = mean_absolute_error(y_test, preds)
    rmse = np.sqrt(mean_squared_error(y_test, preds))
    r2 = r2_score(y_test, preds)
    
    results.append({
        "Model": name,
        "MAE (kW)": mae,
        "RMSE (kW)": rmse,
        "R2 Score": r2
    })

# 5. Model Comparison & Metrics [ANALYSIS]
print("\n--- Step 5: Model Comparison Table ---")
comparison_df = pd.DataFrame(results)
print(comparison_df.to_string(index=False))
comparison_df.to_csv("model_comparison_results.csv", index=False)

# 6. K-Fold Cross-Validation [ROBUSTNESS]
print("\n--- Step 6: 5-Fold Cross-Validation (XGBoost) ---")
from sklearn.model_selection import KFold
kf = KFold(n_splits=5, shuffle=True, random_state=42)
# Using XGBoost as the lead model for CV
cv_scores = cross_val_score(models["XGBoost"], X, y, cv=kf, scoring='r2')
print(f"TimeSeriesSplit R2 Scores: {cv_scores}")
print(f"Mean R2 Score: {cv_scores.mean():.4f}")

# 7. Feature Importance Analysis [INSIGHT]
print("\n--- Step 7: Feature Importance (XGBoost) ---")
xgb_model = trained_models["XGBoost"]
importances = pd.Series(xgb_model.feature_importances_, index=X.columns).sort_values(ascending=False)

plt.figure(figsize=(10, 8))
importances.head(15).plot(kind='barh', color='teal')
plt.title("Top 15 Important Features for Load Prediction")
plt.xlabel("Importance Score")
plt.tight_layout()
plt.savefig("feature_importance.png")
print("Saved feature_importance.png")

# 8. Visualizations [PRESENTATION]
print("\n--- Step 8: Visualizing Results ---")
# Actual vs Predicted (first 200 samples for clarity)
best_model = trained_models["XGBoost"]
y_pred = best_model.predict(X_test)

plt.figure(figsize=(12, 6))
plt.plot(y_test.values[:200], label='Actual Load', color='blue', alpha=0.7)
plt.plot(y_pred[:200], label='Predicted Load (XGBoost)', color='red', linestyle='--', alpha=0.9)
plt.title("System Total Load Prediction (Actual vs Predicted)")
plt.xlabel("Time Samples (Seconds)")
plt.ylabel("Load Demand (kW)")
plt.legend()
plt.tight_layout()
plt.savefig("actual_vs_predicted.png")
print("Saved actual_vs_predicted.png")

# Residual Distribution
residuals = y_test - y_pred
plt.figure(figsize=(10, 6))
sns.histplot(residuals, kde=True, color='purple')
plt.title("Residuals (Error) Distribution")
plt.xlabel("Wait-Time Error (kW)")
plt.tight_layout()
plt.savefig("error_distribution.png")
print("Saved error_distribution.png")

print("\n--- Analysis Complete ---")
