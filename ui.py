import traceback
from aqt import mw
from aqt.qt import QDialog, QVBoxLayout, QLabel, QListWidget, QDialogButtonBox, Qt, qconnect
from aqt.utils import showInfo, showWarning, showText, disable_help_button
from aqt.operations.scheduling import reposition_new_cards
from .deps import check_and_install_deps
from .sorter import extract_and_clean_texts, profile_deck_complexity, execute_sorting_background

def chooseList(prompt: str, choices: list[str], startrow=0, parent=None):

    if not parent:
        parent = mw.app.activeWindow()

    d = QDialog(parent)
    disable_help_button(d)
    d.setWindowModality(Qt.WindowModality.WindowModal)
    accepted = {"ok": False}
    l = QVBoxLayout()
    d.setLayout(l)
    t = QLabel(prompt)
    l.addWidget(t)
    c = QListWidget()
    c.addItems(choices)
    c.setCurrentRow(startrow)
    l.addWidget(c)
    bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)

    def on_accept():
        accepted["ok"] = True
        d.accept()

    def on_reject():
        accepted["ok"] = False
        d.reject()

    qconnect(bb.accepted, on_accept)
    qconnect(bb.rejected, on_reject)
    l.addWidget(bb)
    d.exec()

    if not accepted["ok"]:
        return -1

    return c.currentRow()

def debug_log(msg):
    mw.taskman.run_on_main(lambda: showText(str(msg)))

def on_sorting_finished(result, deck_name):
    mw.progress.finish()
    if not result["success"]:
        showWarning(result["error"])
        return

    try:
        def on_reposition_success(out):
            showInfo(
                f"Sorted {result['count']} new cards in '{deck_name}' by buzz-phrase TF-IDF.\n"
                f"Ignored tag: notAK\n"
                f"Embedding: {result['use_fallback']}\n"
                f"Time elapsed: {result['elapsed']:.2f} s.\n\n"
                f"Press Ctrl+Z to undo."
            )

        reposition_new_cards(
            parent=mw,
            card_ids=result["ordered_cids"],
            starting_from=1,
            step_size=1,
            randomize=False,
            shift_existing=True
        ).success(on_reposition_success).run_in_background()

    except Exception:
        showWarning(f"Error occurred writing results to database:\n{traceback.format_exc()}")

def get_inputs_and_run_sort():
    if not check_and_install_deps():
        return

    decks = mw.col.decks.all_names()
    if not decks:
        showWarning("No decks found.")
        return

    try:
        deck_index = chooseList("Select Deck to Sort", decks, parent=mw)
    except Exception:
        deck_index = None
    if deck_index is None or int(deck_index) < 0 or int(deck_index) >= len(decks):
        return

    deck_name = decks[deck_index]
    field_name = "Text"
    
    data, err = extract_and_clean_texts(deck_name, field_name)
    if err:
        showWarning(err)
        return
        
    all_texts, all_cids = data
    n_cards = len(all_cids)
    try:
        est_fast_direct, est_precision_total = profile_deck_complexity(all_texts)
    except Exception as e:
        showWarning(f"Dry-run profiling failed: {e}")
        return

    def time_string(seconds):
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 120:
            return f"{int(seconds // 60)}m {int(seconds % 60)}s"
        else:
            return f"{int(seconds // 60) + 1}m"

    MAX_WAIT_SECONDS = 10
    mode_choice = 0
    if est_precision_total > MAX_WAIT_SECONDS:
        options = [
            f"Precision Mode (Est. time: {time_string(est_precision_total)}; more accurate)",
            f"Fast Mode (Est. time: {time_string(est_fast_direct)}; less accurate)",
            "Cancel operations (Make no changes)"
        ]
        try:
            idx = chooseList(f"Select Sorting Rigor for {n_cards} Cards", options, parent=mw)
        except Exception:
            idx = None

        if idx is None or idx == -1 or idx >= 2:
            showInfo("Sorting canceled. Deck left unaltered.")
            return
        mode_choice = idx

    mw.progress.start(label="Computing semantic vectors...", immediate=True)
    mw.taskman.run_in_background(
        lambda: execute_sorting_background(all_texts, all_cids, mode_choice),
        lambda fut: on_sorting_finished(fut.result(), deck_name),
    )