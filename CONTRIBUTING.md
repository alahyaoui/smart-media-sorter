# Contributing to Smart Media Sorter

Thank you for your interest in contributing! This project was born from a real need to sort 13,000+ mixed files, and contributions help make it better for everyone.

## 🎯 Ways to Contribute

### 1. Report Bugs
- Check if the bug is already reported in Issues
- Include Python version, OS, and steps to reproduce
- Share sample filenames (anonymized) that caused issues

### 2. Suggest Enhancements
- Describe the use case
- Explain how it would help users
- Consider backward compatibility

### 3. Add Camera Patterns
Different camera brands use different naming patterns. Add yours!

```json
"personal": [
  "DSC_",      // Nikon
  "_MG_",      // Canon
  "P\\d{7}",   // Panasonic
  "YOUR_PATTERN_HERE"
]
```

### 4. Improve Classification
- Submit PRs with better dimension thresholds
- Add support for new file types
- Improve duplicate detection

### 5. Documentation
- Fix typos
- Add examples
- Translate to other languages
- Write blog posts/tutorials

## 🔧 Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/smart-media-sorter.git
cd smart-media-sorter

# No dependencies needed - uses Python standard library!
python3 --version  # Ensure 3.7+

# Run tests
python3 media-sorter.py --source ./test_data --output ./test_output
```

## 📝 Pull Request Process

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Test with real-world data
5. Update README.md if needed
6. Commit with clear messages
7. Push to your fork
8. Open a Pull Request

## 🎨 Code Style

- Follow PEP 8 guidelines
- Use meaningful variable names
- Add docstrings to functions
- Keep functions focused and small
- Comment complex logic

Example:
```python
def classify_by_pattern(self, filename):
    """
    Classify file based on filename patterns.
    
    Args:
        filename: Name of file to classify
        
    Returns:
        Category string or None if no match
    """
    # Implementation
```

## ✅ Testing Guidelines

Before submitting:

1. **Test on sample data**: Create a test folder with various file types
2. **Run dry-run first**: Ensure classification is correct
3. **Test edge cases**: Empty files, special characters, unicode names
4. **Verify output**: Check that files are categorized correctly

## 🐛 Bug Report Template

```markdown
**Description**
A clear description of the bug

**To Reproduce**
1. Run command: `python3 media-sorter.py ...`
2. With files: `file1.jpg, file2.png`
3. See error

**Expected behavior**
What should happen

**Environment**
- OS: [e.g. Ubuntu 22.04]
- Python: [e.g. 3.10.2]
- Version: [e.g. commit hash or release]

**Sample filenames** (anonymized if needed)
- file1.jpg (2MB, 1920x1080)
- file2.png (50KB, 64x64)
```

## 💡 Feature Request Template

```markdown
**Problem**
Describe the problem this feature would solve

**Proposed Solution**
How would this feature work?

**Alternatives Considered**
What other approaches did you think about?

**Use Case**
Real-world example of when this would be useful
```

## 🏆 Recognition

Contributors will be:
- Listed in the project README
- Credited in release notes
- Given maintainer status for significant contributions

## 📜 Code of Conduct

- Be respectful and inclusive
- Accept constructive criticism
- Focus on what's best for the project
- Show empathy towards others

## 🤝 Questions?

- Open a discussion in GitHub Discussions
- Tag issues with `question`
- Check existing issues and docs first

## 📚 Useful Resources

- [Python Standard Library Docs](https://docs.python.org/3/library/)
- [Regular Expressions Guide](https://docs.python.org/3/library/re.html)
- [PEP 8 Style Guide](https://pep8.org/)

---

Thank you for making Smart Media Sorter better! 🎉
