from .models import Category

# Lấy hết category
# Để search, phân loại theo category cho đỡ phải gọi nhiều
def menu_links(request):
    links = Category.objects.all()
    return dict(links = links)