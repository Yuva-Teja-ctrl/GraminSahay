package in.graminsahay.web;

import in.graminsahay.service.NavigatorService;
import in.graminsahay.service.NavigatorService.NavigationResponse;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * REST entry point for the welfare navigator.
 *
 * <p>POST /api/navigate with a situation + optional profile fields; returns the schemes the
 * citizen is (possibly) eligible for, any conflicts, and — if requested — grounded explanations.
 */
@RestController
@RequestMapping("/api")
@CrossOrigin // allow the Next.js frontend during development
public class NavigatorController {

    private final NavigatorService navigatorService;

    public NavigatorController(NavigatorService navigatorService) {
        this.navigatorService = navigatorService;
    }

    @PostMapping("/navigate")
    public NavigationResponse navigate(@Valid @RequestBody NavigateRequest request) {
        return navigatorService.navigate(
                request.situation(),
                request.toProfile(),
                request.explanationsEnabled());
    }
}
