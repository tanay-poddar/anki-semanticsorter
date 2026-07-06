# Semantic Card Sorter (Anki Add-on)

## Overview

This add-on is an Anki extension designed to reorder new, unsuspended flashcards within a specific deck based on their semantic similarity. By grouping conceptually related cards together, it aims to create a more cohesive learning experience. It was built around the AnKing Medical Deck in terms of specific optimization. Use case is designed for ~1000 cards in <5 seconds. Scaling up to ~9000 cards takes <5 minutes. 

## Key Features

- **Semantic Text Processing**: The add-on analyzes the underlying meaning of your cards using Term Frequency-Inverse Document Frequency (TF-IDF) vectorization.
- **Intelligent Text Cleaning**: Before analyzing the text, the add-on automatically strips away Cloze deletion syntax (e.g., `{{c1::...}}`), HTML tags, punctuation, and formatting delimiters to ensure accurate semantic clustering.
- **Medical Deck Optimization**: It features a custom dictionary of `MEDICAL_STOP_WORDS` (such as "diagnosed," "associated," "presents," and "primarily"). This prevents the algorithm from clustering cards based on generic clinical vocabulary and forces it to focus on core concepts.
- **Tag Integration and Filtering**: The add-on includes card tags in its semantic analysis but explicitly ignores the `notAK` tag when processing.
- **Adaptive Performance Profiling**: The tool saves runtime benchmarks locally to `runtime.json`. It uses historical data to predict how long a deck will take to sort. If the estimated time exceeds 10 seconds, it dynamically prompts you to choose between performance and accuracy.
- **Automated Dependency Management**: The add-on automatically detects if required external Python libraries are missing and offers to install them for you directly within Anki.

## How to Use the Add-on

### 1. Initial Setup

1. Open Anki and navigate to the **Tools** menu.
2. Click on the new menu item titled **"Sort New Cards Semantically"**.
3. **Install Dependencies**: If this is your first time running the add-on, it will check for necessary Python packages (`numpy`, `scipy`, and `scikit-learn`). If they are missing, a prompt will ask for permission to install them. Click **Ok** to allow the background installation. 
4. **Restart Anki**: If dependencies were installed, a notification will prompt you to restart Anki before proceeding.

### 2. Sorting a Deck

1. Navigate to **Tools > Sort New Cards Semantically**.
2. **Select a Deck**: A dialog box will appear listing all your available Anki decks. Select the deck containing the new cards you wish to sort and click **Ok**.
3. **Choose Sorting Rigor (If Prompted)**: The add-on extracts the text from the "Text" and "Extra" fields of your new cards and calculates the estimated processing time. If the calculation is estimated to take longer than 10 seconds, you will be prompted to choose a sorting mode:
   - **Precision Mode**: More accurate, utilizing optimal leaf ordering to calculate the best possible hierarchical arrangement, but takes longer.
   - **Fast Mode**: Less accurate but significantly faster for very large decks.
   - **Cancel operations**: Aborts the process and leaves the deck unaltered.
4. **Review Results**: The add-on will execute the sorting in the background. Once finished, a confirmation dialog will display the number of cards sorted, the algorithm used, and the total elapsed time.

### 3. Reverting Changes

If you are unhappy with the new card order, you can immediately press **Ctrl+Z** to undo the repositioning.
