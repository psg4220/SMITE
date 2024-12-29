class EmbedTable:
    def __init__(self, table_data):
        """
        Initialize the EmbedTable with a 2D array of data.

        Args:
            table_data (list[list[str]]): 2D array representing the table.
        """
        self.table_data = table_data

    def generate_table(self):
        """
        Generate the table formatted with backticks for Discord.

        Returns:
            str: A string representing the table with code block formatting.
        """
        if not self.table_data:
            return "```No data available```"

        # Calculate the maximum width of each column
        col_widths = [max(len(str(item)) for item in col) for col in zip(*self.table_data)]

        # Create a formatted table row by row
        table_lines = []
        for row in self.table_data:
            formatted_row = " | ".join(f"{str(item).ljust(width)}" for item, width in zip(row, col_widths))
            table_lines.append(formatted_row)

        # Add a header separator if there's a header row
        if len(self.table_data) > 1:
            header_separator = "-+-".join("-" * width for width in col_widths)
            table_lines.insert(1, header_separator)

        # Return the table as a Discord-friendly code block
        return f"```\n{chr(10).join(table_lines)}\n```"

    def to_embed(self, title=None, description=None, color=0x00FF00):
        """
        Generate a Discord Embed containing the table.

        Args:
            title (str, optional): Title of the embed. Defaults to None.
            description (str, optional): Description of the embed. Defaults to None.
            color (int, optional): Color of the embed. Defaults to 0x00FF00.

        Returns:
            discord.Embed: A Discord Embed object with the table.
        """
        import discord

        table_content = self.generate_table()
        embed = discord.Embed(title=title, description=description, color=color)
        embed.add_field(name="Table", value=table_content, inline=False)

        return embed

# Example usage
if __name__ == "__main__":
    # Example data
    data = []

    data.append(["Trade ID", "Trade Type", "Price", "Amount", "Status", "Date Created"])
    data.append(["1","BUY","12.00","200.00","OPEN","2023"])
    data.append(["2","BUY","12.00","200.00","OPEN","2024"])


    # Create EmbedTable object
    table = EmbedTable(data)

    # Generate a table string
    print(table.generate_table())

    # Example to_embed usage (requires discord.py bot setup)
    # embed = table.to_embed(title="Example Table", description="Here is a table embed!")
