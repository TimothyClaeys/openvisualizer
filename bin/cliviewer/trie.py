class Node:
    def __init__(self, value=None):
        self.children = dict()
        self.value = value


class Trie:
    """
    Implementation of the Trie datastructure.
    """

    def __init__(self):
        self.root = Node(value="")
        self.count = 0
        self.max_len = 0

    def insert(self, word):
        self.count += 1
        self.max_len = max(self.max_len, len(word))

        current = self.root

        for i in range(0, len(word)):
            if word[i] in current.children:
                current = current.children[word[i]]
            else:
                self._add_new_children(current, word, i)
                break

    def starts_with(self, word):
        current = self.root
        ret = -1

        for i in range(0, len(word)):
            if word[i] in current.children:
                current = current.children[word[i]]
                ret = i
            else:
                return ret

        return ret

    def search(self, word):
        current = self.root

        for i in range(0, len(word)):
            if word[i] not in current.children:
                return False
            else:
                current = current.children[word[i]]

        return True

    def _add_new_children(self, node, word, index):
        if word[index] in node.children:
            raise ("This should not happen!")

        while index != len(word):
            node.children[word[index]] = Node(value=node.value + word[index])
            node = node.children[word[index]]
            index += 1

    def print_trie(self):
        matrix = \
            [["_" for i in range(self.max_len)] for j in range(self.count - 1)]
        wordline = 0

        for j in range(self.count - 1):
            matrix[j][0] = '|'

        self._recursive_print(self.root, matrix, wordline)
        for w in range(len(matrix)):
            print("".join(matrix[w]))

    def _recursive_print(self, node, matrix, wordline):
        try:
            matrix[wordline][len(node.value) - 1] = node.value[-1]
        except IndexError:
            pass

        for c in node.children:
            wordline = \
                self._recursive_print(node.children[c], matrix, wordline)

        if len(node.children) == 0:
            for i in range(len(node.value), len(matrix[wordline])):
                matrix[wordline][i] = ''
            return wordline + 1
        else:
            return wordline


if __name__ == "__main__":
    trie = Trie()
    trie.insert("apple")
    trie.insert("application")
    trie.insert("cyclist")
    trie.insert("cycle")
    trie.insert("cycling")
    trie.insert("cyclotron")
    trie.insert("appletree")
    trie.print_trie()

    print(trie.search("apple"))
    print(trie.search("cyclotron"))
    print(trie.search("cyclotrono"))
