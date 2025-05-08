import tkinter as tk
from tkinter import ttk, messagebox

PREFIX = "837S"

class ElisaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ELISA Plate Layout Generator")
        
        # Top frame: select number of plates
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill='x')
        ttk.Label(top_frame, text="Number of plates:").pack(side='left')
        self.num_plates_var = tk.IntVar(value=1)
        ttk.Spinbox(top_frame, from_=1, to=10, width=5, textvariable=self.num_plates_var).pack(side='left', padx=5)
        ttk.Button(top_frame, text="Set", command=self.create_plate_inputs).pack(side='left')

        # Frame for sample inputs
        self.inputs_frame = ttk.Frame(root, padding=10)
        self.inputs_frame.pack(fill='both', expand=True)

        # Generate button
        self.generate_button = ttk.Button(root, text="Generate Layouts", command=self.generate)
        self.generate_button.pack(pady=10)

    def create_plate_inputs(self):
        # Clear previous inputs
        for child in self.inputs_frame.winfo_children():
            child.destroy()
        self.text_boxes = []
        # Create a text box per plate
        for i in range(self.num_plates_var.get()):
            frame = ttk.LabelFrame(self.inputs_frame, text=f"Plate {i+1} Samples (up to 46 numbers, comma-separated)")
            frame.pack(fill='x', pady=5)
            text = tk.Text(frame, height=2, width=60)
            text.pack(padx=5, pady=5)
            self.text_boxes.append(text)

    def format_id(self, num):
        try:
            n = int(num)
        except ValueError:
            return None
        return f"{PREFIX}{n:04d}"

    def generate(self):
        outputs = []
        # Process each plate's entries
        for idx, tb in enumerate(self.text_boxes):
            content = tb.get("1.0", tk.END).strip()
            nums = [s.strip() for s in content.replace(';', ',').split(',') if s.strip()]
            if len(nums) > 46:
                messagebox.showerror("Error", f"Plate {idx+1} can have at most 46 sample numbers.")
                return
            # Convert to formatted IDs
            ids = []
            for n in nums:
                fid = self.format_id(n)
                if fid is None:
                    messagebox.showerror("Error", f"Invalid sample number '{n}' in Plate {idx+1}.")
                    return
                ids.append(fid)
            # Build the 8x12 grid
            grid = self.build_grid(ids)
            outputs.append((idx+1, grid))

        # Show results in a new window with scrollbars
        win = tk.Toplevel(self.root)
        win.title("Generated Plate Layouts")
        for plate_num, grid in outputs:
            lbl = ttk.Label(win, text=f"Plate {plate_num}", font=('Arial', 12, 'bold'))
            lbl.pack(pady=(10,0))
            frame = ttk.Frame(win)
            frame.pack(padx=5)
            # Text widget with horizontal scrollbar
            txt = tk.Text(frame, height=8, wrap='none')
            hbar = ttk.Scrollbar(frame, orient='horizontal', command=txt.xview)
            txt.configure(xscrollcommand=hbar.set)
            txt.grid(row=0, column=0, sticky='nsew')
            hbar.grid(row=1, column=0, sticky='ew')
            frame.grid_columnconfigure(0, weight=1)

            # Insert rows
            for row in grid:
                txt.insert(tk.END, "\t".join(row) + "\n")
            txt.config(state='disabled')

    def build_grid(self, sample_ids):
        # Create empty 8x12 grid
        grid = [["" for _ in range(12)] for _ in range(8)]
        # Column 0: Pos and Neg controls
        grid[0][0] = grid[1][0] = "PosCtrl"
        grid[2][0] = grid[3][0] = "NegCtrl"
        # First two samples (if provided)
        if len(sample_ids) > 0:
            grid[4][0] = grid[5][0] = sample_ids[0]
        if len(sample_ids) > 1:
            grid[6][0] = grid[7][0] = sample_ids[1]
        # Columns 1-11: up to 44 remaining samples in duplicate
        for col in range(1, 12):
            for i in range(4):
                idx = 2 + (col - 1) * 4 + i
                if idx < len(sample_ids):
                    sid = sample_ids[idx]
                    r = i * 2
                    grid[r][col] = grid[r+1][col] = sid
        return grid

if __name__ == "__main__":
    root = tk.Tk()
    app = ElisaApp(root)
    root.mainloop()
