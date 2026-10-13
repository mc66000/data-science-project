# Palmer Penguins: Predicting Species from Body Measurements

## 1. Research Question
Can four simple body measurements (bill length, bill depth, flipper length,
body mass) reliably distinguish the three penguin species (Adelie, Chinstrap,
Gentoo) observed in the Palmer Archipelago, Antarctica?

## 2. Dataset Source and Usage Permissions
- **Source:** Palmer Penguins dataset (Gorman, Williams & Fraser, 2014),
  distributed via the `palmerpenguins` R package and bundled with `seaborn`.
- **Licence:** CC0 1.0 (Public Domain) – free to use, share and adapt.
- **Size:** 344 observations, 7 variables; 333 rows after removing missing values.
- No personal data or restricted information is involved.

## 3. Methods and Tools
| Step | Tool |
|------|------|
| Data loading & cleaning | pandas, seaborn |
| Exploratory visualization | seaborn, matplotlib |
| Classification | scikit-learn (StandardScaler + LogisticRegression) |
| Evaluation | accuracy, precision/recall, confusion matrix |

Data were split 75/25 (stratified, `random_state=42`).

## 4. Key Findings
- **Flipper length and body mass separate Gentoo clearly** from the other two
  species (Fig. 1). Gentoo penguins are larger on both dimensions.
- **Bill length separates Adelie from Chinstrap** (Fig. 2); the two species
  overlap in body size but Chinstrap bills are notably longer.
- A simple logistic regression reaches **~98–100% test accuracy** using only
  the four measurements.

![Fig 1](figures/fig1_flipper_vs_mass.png)
![Fig 2](figures/fig2_bill_length_by_species.png)

### Limitation
The dataset is small (333 rows) and comes from only three islands sampled in
2007–2009. The model may not generalise to other colonies, seasons or
juvenile birds, and the near-perfect accuracy partly reflects how well-separated
these three species already are.

## 5. How to Run
```bash
git clone https://github.com/【your-username】/data-science-project.git
cd data-science-project
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python analysis.py
