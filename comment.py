# To use this file from the "Preferences" menu choose "Browse Packages..."
# In that folder create a new folder named "Default"
# In the "Default" folder save this file as "comment.py"

import sublime
import sublime_plugin


def advance_to_first_non_white_space_on_line(view, pt):
    while True:
        c = view.substr(pt)
        if c == " " or c == "\t":
            pt += 1
        else:
            break

    return pt


def has_non_white_space_on_line(view, pt):
    while True:
        c = view.substr(pt)
        if c == " " or c == "\t":
            pt += 1
        else:
            return c != "\n"


def build_comment_data(view, pt):
    shell_vars = view.meta_info("shellVariables", pt)
    if not shell_vars:
        return ([], [])

    # transform the list of dicts into a single dict
    all_vars = {}
    for v in shell_vars:
        if 'name' in v and 'value' in v:
            all_vars[v['name']] = v['value']

    line_comments = []
    block_comments = []

    # transform the dict into a single array of valid comments
    suffixes = [""] + ["_" + str(i) for i in range(1, 10)]
    for suffix in suffixes:
        start = all_vars.setdefault("TM_COMMENT_START" + suffix)
        end = all_vars.setdefault("TM_COMMENT_END" + suffix)
        disable_indent = all_vars.setdefault("TM_COMMENT_DISABLE_INDENT" + suffix)

        if start and end:
            block_comments.append((start, end, disable_indent == 'yes'))
            block_comments.append((start.strip(), end.strip(), disable_indent == 'yes'))
        elif start:
            line_comments.append((start, disable_indent == 'yes'))
            line_comments.append((start.strip(), disable_indent == 'yes'))

    return (line_comments, block_comments)


class ToggleCommentCommand(sublime_plugin.TextCommand):
    def remove_block_comment(self, view, edit, comment_data, region):
        (line_comments, block_comments) = comment_data

        # Call extract_scope from the midpoint of the region, as calling it
        # from the start can give false results if the block comment begin/end
        # markers are assigned their own scope, as is done in HTML.
        whole_region = view.extract_scope(region.begin() + region.size() / 2)

        if BetterJSComments.is_js(view):
            lc_region = self.is_entirely_line_commented(view, comment_data, region)
            lc_whole_region = self.is_entirely_line_commented(view, comment_data, whole_region)
            if lc_region and lc_whole_region:
                return self.remove_line_comment(view, edit, comment_data, whole_region)

        for c in block_comments:
            (start, end, disable_indent) = c
            start_region = sublime.Region(whole_region.begin(), whole_region.begin() + len(start))
            end_region = sublime.Region(whole_region.end() - len(end), whole_region.end())

            if view.substr(start_region) == start and view.substr(end_region) == end:
                # It's faster to erase the start region first
                view.erase(edit, start_region)

                end_region = sublime.Region(
                    end_region.begin() - start_region.size(),
                    end_region.end() - start_region.size())

                view.erase(edit, end_region)
                return True

        return False

    def remove_line_comment(self, view, edit, comment_data, region):
        (line_comments, block_comments) = comment_data

        if BetterJSComments.is_js(view):
            line_comments = BetterJSComments.line_comments()

        found_line_comment = False

        start_positions = [advance_to_first_non_white_space_on_line(
            view, r.begin()) for r in view.lines(region)]
        start_positions.reverse()

        for pos in start_positions:
            for c in line_comments:
                (start, disable_indent) = c
                comment_region = sublime.Region(pos, pos + len(start))
                if view.substr(comment_region) == start:
                    view.erase(edit, comment_region)
                    found_line_comment = True
                    break

        return found_line_comment

    def is_entirely_line_commented(self, view, comment_data, region):
        (line_comments, block_comments) = comment_data

        if BetterJSComments.is_js(view):
            line_comments = BetterJSComments.line_comments()

        start_positions = [advance_to_first_non_white_space_on_line(
            view, r.begin()) for r in view.lines(region)]
        start_positions = list(filter(
            lambda p: has_non_white_space_on_line(view, p), start_positions))

        if len(start_positions) == 0:
            return False

        for pos in start_positions:
            found_line_comment = False
            for c in line_comments:
                (start, disable_indent) = c
                comment_region = sublime.Region(pos, pos + len(start))
                if view.substr(comment_region) == start:
                    found_line_comment = True
            if not found_line_comment:

                return False

        return True

    def block_comment_region(self, view, edit, block_comment_data, region):
        (start, end, disable_indent) = block_comment_data

        if region.empty():
            # Silly buggers to ensure the cursor doesn't end up after the end
            # comment token
            view.replace(edit, sublime.Region(region.end()), 'x')
            view.insert(edit, region.end() + 1, end)
            view.replace(edit, sublime.Region(region.end(), region.end() + 1), '')
            view.insert(edit, region.begin(), start)
        else:
            view.insert(edit, region.end(), end)
            view.insert(edit, region.begin(), start)

    def line_comment_region(self, view, edit, line_comment_data, region):
        (start, disable_indent) = line_comment_data

        num_of_lines = len(view.lines(region))
        if not BetterJSComments.is_js(view) or num_of_lines == 1:

            start_positions = [r.begin() for r in view.lines(region)]
            start_positions.reverse()

            # Remove any blank lines from consideration, they make getting the
            # comment start markers to line up challenging
            non_empty_start_positions = list(filter(
                lambda p: has_non_white_space_on_line(view, p), start_positions))

            # If all the lines are blank however, just comment away
            if len(non_empty_start_positions) != 0:
                start_positions = non_empty_start_positions

            if not disable_indent:
                min_indent = None

                # This won't work well with mixed spaces and tabs, but really,
                # don't do that!
                for pos in start_positions:
                    indent = advance_to_first_non_white_space_on_line(view, pos) - pos
                    if min_indent is None or indent < min_indent:
                        min_indent = indent

                if min_indent is not None and min_indent > 0:
                    start_positions = [r + min_indent for r in start_positions]

            for pos in start_positions:
                view.insert(edit, pos, start)

        else:
            # Since we are using block comments as if they are line comments then the trailing
            # block comment needs to be on a new line.  Otherwise the block comment would end at
            # the start of the line and the code after that would be run, even though that line
            # was selected when the "comment line" hotkey was pressed.
            # Create a new region from the start of the original region, to the start of the line
            # after the current last line.
            begin = region.begin()
            end = region.end()

            last_line = view.line(end)
            end = view.full_line(end).end()
            # Only add another line if the last line of the comment isn't empty
            if not last_line.empty():
                end += 1

            new_region = sublime.Region(begin, end)

            # Comment strings and start positions need to be reversed because if view.insert()
            # is called in order (top to bottom) then it doesn't work.  No idea why.
            start_positions = [r.begin() for r in view.lines(new_region)]
            start_positions.reverse()

            # Recount the number of lines since it may have increased by 1
            num_of_lines = len(start_positions)

            # If we are using BetterJSComments we are going to comment all blank lines
            # and the starting comment for each line will be variable
            comment_strings = BetterJSComments.comment_strings(num_of_lines)
            comment_strings = comment_strings[::-1]

            for pos, start in zip(start_positions, comment_strings):
                view.insert(edit, pos, start)

    def add_comment(self, view, edit, comment_data, prefer_block, region):
        (line_comments, block_comments) = comment_data

        if len(line_comments) == 0 and len(block_comments) == 0:
            return

        if len(block_comments) == 0:
            prefer_block = False

        if len(line_comments) == 0:
            prefer_block = True

        if region.empty():
            if prefer_block:
                # add the block comment
                self.block_comment_region(view, edit, block_comments[0], region)
            else:
                # comment out the line
                self.line_comment_region(view, edit, line_comments[0], region)
        else:
            if prefer_block:
                # add the block comment
                self.block_comment_region(view, edit, block_comments[0], region)
            else:
                # add a line comment to each line
                self.line_comment_region(view, edit, line_comments[0], region)

    def run(self, edit, block=False):
        for region in self.view.sel():
            comment_data = build_comment_data(self.view, region.begin())
            if (region.end() != self.view.size() and
                    build_comment_data(self.view, region.end()) != comment_data):
                # region spans languages, nothing we can do
                continue

            if self.remove_block_comment(self.view, edit, comment_data, region):
                continue

            if self.is_entirely_line_commented(self.view, comment_data, region):
                self.remove_line_comment(self.view, edit, comment_data, region)
                continue

            has_line_comment = len(comment_data[0]) > 0

            if not has_line_comment and not block and region.empty():
                # Use block comments to comment out the line
                line = self.view.line(region.a)
                line = sublime.Region(
                    advance_to_first_non_white_space_on_line(self.view, line.a), line.b)

                # Try and remove any existing block comment now
                if self.remove_block_comment(self.view, edit, comment_data, line):
                    continue

                self.add_comment(self.view, edit, comment_data, block, line)
                continue

            # Add a comment instead
            self.add_comment(self.view, edit, comment_data, block, region)


class BetterJSComments(object):

    def is_js(view):
        disabled = False

        if disabled:
            return False

        # Check if the current view is using Javascript or JSON syntax
        syntax = view.settings().get('syntax')
        if syntax == 'Packages/JavaScript/JavaScript.sublime-syntax':
            return True
        if syntax == 'Packages/JavaScript/JSON.sublime-syntax':
            return True
        return False

    def line_comments():
        # Return list of items that indicate a region is line commented
        # Zeroes are because it's expecting boolean to indicate indentation required, but not being
        # used when checking "is_entirely_line_commented"
        # Last item is the default line comment
        return [('/*\\', 0),
                ('\|/', 0),
                ('|||', 0),
                ('|||', 0),
                ('/|\\', 0),
                ('\*/', 0),
                ('// ', 1)]

    def comment_strings(num_of_lines):
        # Build a list of comment strings that can be zipped together with all the lines
        # being commented
        start = '/*\\'
        end = '\*/'
        odd_sep = '|||'
        evens = ['\|/', '/|\\']

        comment_list = []
        comment_list.append(start)
        # Build the comment list assuming there are an even number of lines
        for i in range(num_of_lines-2):
            # Add alternating even pieces
            comment_list.append(evens[i % 2])

        # Check to see if a midpoint needs to be inserted for odd number of lines
        if num_of_lines % 2:
            # If it does then insert it at the current midpoint of the comment list and trim the
            # last even comment off the chain before adding the endcap
            comment_list.insert(num_of_lines // 2, odd_sep)
            comment_list = comment_list[:-1]

        comment_list.append(end)
        return comment_list
