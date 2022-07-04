from django_filters import filters, rest_framework as rest_framework_filters


class PropertyListCharFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value not in filters.EMPTY_VALUES:
            value = [str(item) for item in value.split(",")]
            filtered_pks = [el.pk for el in qs if el.change_state in value]
            return qs.filter(pk__in=filtered_pks)
        return super().filter(qs, value)


class ListCharFilter(filters.CharFilter):
    def filter(self, qs, value):
        if value not in filters.EMPTY_VALUES and self.lookup_expr == "in":
            value = [str(item) for item in value.split(",")]
        return super().filter(qs, value)


class ListNumberFilter(filters.NumberFilter):
    def filter(self, qs, value):
        if self.lookup_expr == "in":
            value = [int(item) for item in value.split(",")]
        return super().filter(qs, value)


class UnionFilterBackend(rest_framework_filters.DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        """
        TODO: implementing union operator(+, |) for filter_backends could be useful in the future, like permissions
        Not completed
        """
        for backend in view.filter_backends_union:
            queryset |= backend().filter_queryset(request, queryset, view)
        queryset = super().filter_queryset(request, queryset.distinct(), view)
        return queryset
