# Contributing to PharmaAssist AI

Thank you for your interest in contributing to PharmaAssist AI! This document provides guidelines for contributing to the project.

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/yourusername/pharma-assist-ai.git
   cd pharma-assist-ai
   ```
3. **Set up the development environment**:
   ```bash
   cp .env.example .env
   # Add your GROQ_API_KEY to .env
   pip install -r requirements/dev.txt
   ```

## 🔧 Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-bug-fix
```

Branch naming conventions:
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions or updates

### 2. Make Your Changes

- Write clean, readable code
- Follow existing code style and patterns
- Add comments for complex logic
- Update documentation if needed

### 3. Test Your Changes

```bash
# Run tests
python tests/test_db_tools.py

# Test setup
python test_setup.py

# Manual testing
python start_server.py
```

### 4. Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

Commit message format:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Test additions or updates
- `chore:` - Maintenance tasks

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear title and description
- Reference any related issues
- Screenshots (if UI changes)
- Test results

## 📝 Code Style Guidelines

### Python

- Follow PEP 8 style guide
- Use type hints where appropriate
- Maximum line length: 100 characters
- Use docstrings for functions and classes

Example:
```python
def process_order(order_id: str, customer_id: str) -> dict:
    """
    Process an order for a customer.
    
    Args:
        order_id: The order identifier
        customer_id: The customer identifier
        
    Returns:
        dict: Order processing result
    """
    # Implementation
    pass
```

### TypeScript/JavaScript

- Use TypeScript for type safety
- Follow ESLint configuration
- Use meaningful variable names
- Add JSDoc comments for complex functions

## 🧪 Testing Guidelines

- Add tests for new features
- Ensure existing tests pass
- Test edge cases and error conditions
- Include integration tests for API endpoints

## 📚 Documentation

- Update README.md if adding new features
- Add inline comments for complex logic
- Update API documentation
- Include usage examples

## 🐛 Reporting Bugs

When reporting bugs, please include:

1. **Description** - Clear description of the bug
2. **Steps to Reproduce** - Detailed steps to reproduce the issue
3. **Expected Behavior** - What you expected to happen
4. **Actual Behavior** - What actually happened
5. **Environment** - OS, Python version, dependencies
6. **Screenshots** - If applicable
7. **Logs** - Relevant error messages or logs

## 💡 Suggesting Features

When suggesting features, please include:

1. **Use Case** - Why is this feature needed?
2. **Proposed Solution** - How should it work?
3. **Alternatives** - Other approaches considered
4. **Additional Context** - Any other relevant information

## 🔍 Code Review Process

1. All submissions require review
2. Reviewers will check:
   - Code quality and style
   - Test coverage
   - Documentation
   - Performance impact
3. Address review comments
4. Once approved, maintainers will merge

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows project style guidelines
- [ ] Tests added/updated and passing
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] Branch is up to date with main
- [ ] No merge conflicts
- [ ] PR description is complete

## 🎯 Areas for Contribution

We especially welcome contributions in:

- **New Features** - Additional intents, tools, or capabilities
- **Testing** - Improved test coverage
- **Documentation** - Better guides and examples
- **Performance** - Optimization improvements
- **Bug Fixes** - Resolving issues
- **UI/UX** - Frontend improvements

## 🤝 Community Guidelines

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Follow the code of conduct

## 📞 Getting Help

- Open an issue for questions
- Check existing issues and PRs
- Review documentation
- Ask in discussions

## 🙏 Thank You!

Your contributions make this project better for everyone. We appreciate your time and effort!

---

**Questions?** Open an issue or start a discussion on GitHub.
