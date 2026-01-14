from fpdf import FPDF

class PDF(FPDF):
    def header(self):
        # No header for a clean look, or un-comment below to add one
        # self.set_font('Arial', 'B', 12)
        # self.cell(0, 10, 'DATA / DATE: .................', 0, 1, 'R')
        pass

    def footer(self):
        # Position at 1.5 cm from bottom
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128) # Gray color
        # The "Smaller Cat" joke in the footer
        # self.cell(0, 10, '(tu jest bardzo mały kot / here is a very small cat)  ᓚᘏᗢ', 0, 0, 'C')

    def draw_lines(self):
        # Set line color to light gray
        self.set_draw_color(200, 200, 200) 
        # Line spacing (Wide rule for "Big Letters")
        line_height = 10 
        # Margins
        top_margin = 25
        bottom_margin = 25
        
        # Draw lines from top to bottom
        y = top_margin
        while y < (228.6 - bottom_margin): # 9 inches is 228.6mm
            self.line(15, y, 137.4, y) # 6 inches width approx 152mm, minus margins
            y += line_height

def create_kdp_interior(filename):
    # KDP Standard 6x9 inches
    # Unit=mm, format=(152.4, 228.6) which is 6x9 inches
    pdf = PDF(orientation='P', unit='mm', format=(152.4, 228.6))
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Create 110 pages
    for i in range(110):
        pdf.add_page()
        pdf.draw_lines()
        
    pdf.output(filename)
    print(f"Success! {filename} created.")

# Run the function
create_kdp_interior("Notes_Maly_Kot_6x9.pdf")